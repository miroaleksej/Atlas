#!/usr/bin/env python3
"""Thin instrument I/O adapters for Φ-Compiler v3.0.

No recovery, posterior, calibration, safety-design, drift or controller algorithm
lives here. Adapters only translate a pre-certified HardwareExperimentSpec to instrument
commands and return RawAcquisition objects.
"""
from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from source.phi_compiler_owner import HardwareExperimentSpec, InstrumentIdentity, RawAcquisition, SafetyEnvelope, hardware_experiment_input


class InstrumentTransportError(RuntimeError):
    pass


class RedPitayaSCPIAdapter:
    """Standard-buffer Red Pitaya SCPI adapter; no AXI deep-memory claim."""

    BASE_SAMPLE_RATE_HZ = 125_000_000.0
    BUFFER_SIZE = 16_384
    DECIMATIONS = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536)

    def __init__(
        self,
        host: str,
        safety_envelope: SafetyEnvelope,
        *,
        port: int = 5000,
        timeout_s: float = 5.0,
        output_channel: int = 1,
        input_channels: Sequence[int] = (1, 2),
        relay_enable_pin: str = "DIO2_P",
        relay_feedback_pin: str = "DIO3_P",
        relay_active_high: bool = True,
    ) -> None:
        self.host=host; self.port=int(port); self.timeout_s=float(timeout_s)
        self.output_channel=int(output_channel); self.input_channels=tuple(int(ch) for ch in input_channels)
        if not self.input_channels or any(ch not in (1,2) for ch in self.input_channels):
            raise ValueError("input_channels must contain Red Pitaya fast channels 1 and/or 2")
        self.relay_enable_pin=str(relay_enable_pin); self.relay_feedback_pin=str(relay_feedback_pin)
        if self.relay_enable_pin == self.relay_feedback_pin:
            raise ValueError("relay enable and feedback pins must be distinct")
        self.relay_active_high=bool(relay_active_high)
        self.safety_envelope=safety_envelope; self.safety_envelope.validate()
        self._sock: socket.socket | None=None; self._spec: HardwareExperimentSpec | None=None; self._decimation: int | None=None
        self._last_arm_monotonic: float | None=None

    def _connect(self) -> socket.socket:
        if self._sock is None:
            self._sock=socket.create_connection((self.host,self.port),timeout=self.timeout_s)
            self._sock.settimeout(self.timeout_s)
        return self._sock

    def _write(self, command: str) -> None:
        try: self._connect().sendall((command.strip()+"\r\n").encode("ascii"))
        except OSError as exc: raise InstrumentTransportError(command) from exc

    def _query(self, command: str) -> str:
        self._write(command); chunks=[]
        try:
            while True:
                part=self._connect().recv(65536)
                if not part: break
                chunks.append(part)
                if b"\n" in part: break
        except OSError as exc: raise InstrumentTransportError(command) from exc
        if not chunks: raise InstrumentTransportError(f"empty response: {command}")
        return b"".join(chunks).decode("ascii",errors="strict").strip()

    def identity(self) -> InstrumentIdentity:
        raw=self._query("*IDN?")
        parts=[p.strip() for p in raw.split(",")]
        return InstrumentIdentity(parts[0] if parts else "Red Pitaya", parts[1] if len(parts)>1 else "UNKNOWN", parts[2] if len(parts)>2 else "UNKNOWN", parts[3] if len(parts)>3 else "UNKNOWN", f"TCP-SCPI:{self.host}:{self.port}")

    def _choose_decimation(self, observation_time: float) -> int:
        for dec in self.DECIMATIONS:
            rate=self.BASE_SAMPLE_RATE_HZ/dec
            if rate < self.safety_envelope.min_sample_rate_hz: continue
            if observation_time*rate <= self.BUFFER_SIZE: return dec
        raise ValueError("Requested observation window does not fit standard buffer without violating minimum sample rate")

    def initialize_safety_io(self) -> None:
        """Put the external fail-safe relay in the de-energized state and verify feedback."""
        self._write(f"DIG:PIN:DIR OUT,{self.relay_enable_pin}")
        self._write(f"DIG:PIN:DIR IN,{self.relay_feedback_pin}")
        self.set_relay_enabled(False)
        if self.relay_feedback_closed():
            raise InstrumentTransportError("Fail-safe relay reports CLOSED while commanded OFF")

    def set_relay_enabled(self, enabled: bool) -> None:
        level = int(bool(enabled) == self.relay_active_high)
        self._write(f"DIG:PIN {self.relay_enable_pin},{level}")

    def relay_feedback_closed(self) -> bool:
        raw = self._query(f"DIG:PIN? {self.relay_feedback_pin}").strip().upper()
        if raw not in {"0", "1", "LOW", "HIGH", "OFF", "ON"}:
            raise InstrumentTransportError(f"Unexpected relay feedback: {raw!r}")
        state = raw in {"1", "HIGH", "ON"}
        return state if self.relay_active_high else not state

    def prove_hardware_emergency_stop(self) -> Mapping[str, Any]:
        """Exercise relay close/open feedback with the analog output held OFF."""
        self._write(f"OUTPUT{self.output_channel}:STATE OFF")
        self.initialize_safety_io()
        open_before = not self.relay_feedback_closed()
        self.set_relay_enabled(True)
        time.sleep(0.03)
        closed = self.relay_feedback_closed()
        self.set_relay_enabled(False)
        time.sleep(0.03)
        open_after = not self.relay_feedback_closed()
        if not (open_before and closed and open_after):
            self.emergency_stop(best_effort=True)
            raise InstrumentTransportError("Hardware relay emergency-stop proof failed")
        return {"open_before": open_before, "closed_when_armed": closed, "open_after": open_after}

    def configure(self, spec: HardwareExperimentSpec) -> None:
        spec.validate()
        if not spec.safe(): raise ValueError("HardwareExperimentSpec failed validation")
        if max(abs(spec.amplitude_1),abs(spec.amplitude_2))>self.safety_envelope.max_abs_drive: raise ValueError("Drive exceeds SafetyEnvelope")
        self.initialize_safety_io()
        self._write(f"OUTPUT{self.output_channel}:STATE OFF")
        if spec.energy()>self.safety_envelope.max_energy or spec.observation_time>self.safety_envelope.max_observation_time: raise ValueError("Energy/time exceeds SafetyEnvelope")
        self._decimation=self._choose_decimation(spec.observation_time)
        t=np.linspace(0.0,spec.observation_time,self.BUFFER_SIZE,endpoint=False)
        waveform=hardware_experiment_input(t,spec)
        peak=float(np.max(np.abs(waveform)))
        normalized=waveform/max(peak,1e-12)
        data=",".join(f"{float(v):.8g}" for v in normalized)
        ch=self.output_channel
        self._write("GEN:RST")
        self._write(f"SOUR{ch}:FUNC ARBITRARY")
        self._write(f"SOUR{ch}:TRAC:DATA:DATA {data}")
        self._write(f"SOUR{ch}:VOLT {peak:.12g}")
        self._write(f"SOUR{ch}:BURS:STAT BURST")
        self._write(f"SOUR{ch}:BURS:NCYC 1")
        self._write(f"SOUR{ch}:BURS:NOR 1")
        self._write(f"SOUR{ch}:TRIG:SOUR INT")
        self._write(f"ACQ:DEC {self._decimation}")
        self._write("ACQ:TRIG:LEV 0")
        self._spec=spec

    def arm(self) -> None:
        if self._spec is None or self._decimation is None: raise RuntimeError("configure must precede arm")
        self._write("ACQ:STOP"); self._write("ACQ:RST"); self._write("ACQ:START")
        self._write(f"OUTPUT{self.output_channel}:STATE ON")
        self.set_relay_enabled(True)
        time.sleep(0.01)
        if not self.relay_feedback_closed():
            self.emergency_stop(best_effort=True)
            raise InstrumentTransportError("Fail-safe relay did not close before trigger")
        self._last_arm_monotonic=time.monotonic()
        self._write(f"SOUR{self.output_channel}:TRIG:INT")
        self._write("ACQ:TRIG NOW")

    @staticmethod
    def _parse_ascii_array(raw: str) -> np.ndarray:
        cleaned=raw.strip().strip("{}").strip()
        if not cleaned: return np.empty(0,float)
        return np.asarray([float(v) for v in cleaned.split(",")],float)

    def acquire(self) -> RawAcquisition:
        if self._spec is None or self._decimation is None: raise RuntimeError("configure/arm required")
        deadline=time.monotonic()+self.timeout_s
        while time.monotonic()<deadline:
            status=self._query("ACQ:TRIG:STAT?").upper()
            if "TD" in status: break
            time.sleep(0.01)
        else:
            self.emergency_stop(best_effort=True); raise InstrumentTransportError("acquisition trigger timeout")
        channels={}
        for input_channel in self.input_channels:
            values=self._parse_ascii_array(self._query(f"ACQ:SOUR{input_channel}:DATA:TRIG? 0,{self.BUFFER_SIZE}"))
            if len(values)!=self.BUFFER_SIZE:
                self.emergency_stop(best_effort=True); raise InstrumentTransportError(f"expected {self.BUFFER_SIZE} samples on IN{input_channel}, got {len(values)}")
            channels[f"in{input_channel}"]=values
        rate=self.BASE_SAMPLE_RATE_HZ/self._decimation
        t=np.arange(self.BUFFER_SIZE,dtype=float)/rate
        latency_s=None if self._last_arm_monotonic is None else max(time.monotonic()-self._last_arm_monotonic,0.0)
        return RawAcquisition(t=t,channels=channels,metadata={"sample_rate_hz":rate,"decimation":self._decimation,"buffer_size":self.BUFFER_SIZE,"source":"RED_PITAYA_SCPI","latency_s":latency_s,"relay_feedback_closed":self.relay_feedback_closed()})

    def emergency_stop(self, best_effort: bool=False) -> None:
        errors=[]
        try:
            self.set_relay_enabled(False)
        except Exception as exc:
            errors.append(exc)
        for command in (f"OUTPUT{self.output_channel}:STATE OFF","ACQ:STOP","GEN:RST"):
            try: self._write(command)
            except Exception as exc: errors.append(exc)
        if errors and not best_effort: raise InstrumentTransportError(f"emergency stop incomplete: {errors}")

    def close(self) -> None:
        if self._sock is not None:
            try:
                self.emergency_stop(best_effort=True)
            finally:
                try: self._sock.close()
                finally: self._sock=None
    def __enter__(self) -> "RedPitayaSCPIAdapter": return self
    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if exc is not None:
            try: self.emergency_stop(best_effort=True)
            except Exception: pass
        self.close()


@dataclass(frozen=True)
class PyVISACommandProfile:
    reset_command: str
    stop_command: str
    output_off_command: str
    configure_commands: Sequence[str]
    arm_commands: Sequence[str]
    waveform_command: str
    acquisition_query: str
    sample_rate_query: str
    channel_name: str = "response"
    binary_datatype: str = "f"
    binary_is_big_endian: bool = False


class PyVISAInstrumentAdapter:
    """Profile-driven VISA adapter; vendor commands are explicit, never guessed."""
    def __init__(self, resource_name: str, profile: PyVISACommandProfile, safety_envelope: SafetyEnvelope, *, backend: str | None=None, timeout_ms: int=5000) -> None:
        self.resource_name=resource_name; self.profile=profile; self.safety_envelope=safety_envelope; self.safety_envelope.validate()
        self.backend=backend; self.timeout_ms=int(timeout_ms); self._rm=None; self._resource=None; self._spec: HardwareExperimentSpec | None=None
    def _open(self) -> None:
        if self._resource is not None: return
        try: import pyvisa
        except ImportError as exc: raise RuntimeError("PyVISA backend requires pyvisa") from exc
        self._rm=pyvisa.ResourceManager(self.backend) if self.backend else pyvisa.ResourceManager()
        self._resource=self._rm.open_resource(self.resource_name); self._resource.timeout=self.timeout_ms
    def identity(self) -> InstrumentIdentity:
        self._open(); raw=str(self._resource.query("*IDN?")).strip(); parts=[p.strip() for p in raw.split(",")]
        return InstrumentIdentity(parts[0] if parts else "UNKNOWN",parts[1] if len(parts)>1 else "UNKNOWN",parts[2] if len(parts)>2 else "UNKNOWN",parts[3] if len(parts)>3 else "UNKNOWN",f"VISA:{self.resource_name}")
    def configure(self, spec: HardwareExperimentSpec) -> None:
        spec.validate()
        if not spec.safe(): raise ValueError("HardwareExperimentSpec failed validation")
        if max(abs(spec.amplitude_1),abs(spec.amplitude_2))>self.safety_envelope.max_abs_drive: raise ValueError("Drive exceeds SafetyEnvelope")
        self._open(); t=np.linspace(0.0,spec.observation_time,16384,endpoint=False); waveform=hardware_experiment_input(t,spec)
        self._resource.write(self.profile.reset_command)
        for command in self.profile.configure_commands: self._resource.write(command.format(spec=spec))
        self._resource.write_binary_values(self.profile.waveform_command,waveform,datatype=self.profile.binary_datatype,is_big_endian=self.profile.binary_is_big_endian)
        self._spec=spec
    def arm(self) -> None:
        if self._spec is None: raise RuntimeError("configure must precede arm")
        for command in self.profile.arm_commands: self._resource.write(command)
    def acquire(self) -> RawAcquisition:
        if self._spec is None: raise RuntimeError("configure/arm required")
        values=np.asarray(self._resource.query_binary_values(self.profile.acquisition_query,datatype=self.profile.binary_datatype,is_big_endian=self.profile.binary_is_big_endian,container=np.array),float)
        sample_rate=float(self._resource.query(self.profile.sample_rate_query))
        if sample_rate<self.safety_envelope.min_sample_rate_hz or len(values)<16: raise InstrumentTransportError("invalid acquisition sample rate or length")
        return RawAcquisition(np.arange(len(values),dtype=float)/sample_rate,{self.profile.channel_name:values},{"sample_rate_hz":sample_rate,"source":"PYVISA","resource":self.resource_name})
    def emergency_stop(self) -> None:
        self._open(); errors=[]
        for command in (self.profile.output_off_command,self.profile.stop_command):
            try: self._resource.write(command)
            except Exception as exc: errors.append(exc)
        if errors: raise InstrumentTransportError(f"emergency stop incomplete: {errors}")
    def close(self) -> None:
        if self._resource is not None:
            self._resource.close(); self._resource=None
        if self._rm is not None:
            self._rm.close(); self._rm=None
