"""Process-separated synthetic control for measurement-driven axis research.

This world is authored for testing a bounded representation class. Recovering it
is not scientific novelty. The researcher receives samples and adapter replies,
not the environment's parameters or callable response function.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np

from source.lawspace.closed_loop_research import ClosedLoopResearchOwner, seal
from source.lawspace.schema import digest_payload


def _world(connection, seed: int, mode: str) -> None:
    rng = np.random.default_rng(seed)
    center = float(rng.uniform(3.5, 6.5))
    width = float(rng.uniform(0.6, 1.0))
    amplitude = float(rng.uniform(4, 7))

    def value(point, sealed=False):
        x, z = point['p'], point['q']
        if mode == 'noise':
            return float(rng.normal(0, 2))
        bump = amplitude * np.exp(-0.5 * ((x-center)/width)**2) * (1 - 0.45*z)
        return float(1 + 0.3*x + 0.2*z + (-bump if sealed and mode == 'shift' else bump))

    def dataset(points, regimes, sealed=False):
        return dict(dataset_id='SEALED' if sealed else 'DISCOVERY', observable_id='response',
                    observable_units='1', y=[value(p, sealed) for p in points], sigma=None,
                    regime_ids=regimes, provenance='SYNTHETIC_PROCESS_WORLD',
                    axes=[dict(axis_id=a, domain='physics', units='1',
                               provenance='SYNTHETIC_PROCESS_WORLD', values=[p[a] for p in points])
                          for a in ('p', 'q')])

    points = [dict(p=float(x), q=float(z)) for offset in (0, 0.08)
              for z in (0, 1) for x in np.linspace(0, 10, 41) + offset]
    initial = dataset(points, ['FIT']*82 + ['VALIDATION']*82)
    # Reserve independent inputs before research starts; no reseeding after reveal.
    hold_points = [dict(p=float(x), q=float(z)) for z in (0, 1)
                   for x in rng.uniform(0.02, 10.0, 80)]
    holdout = dataset(hold_points, ['FINAL']*len(hold_points), True)
    connection.send({'dataset': initial, 'holdout_dataset_digest': digest_payload(holdout)})
    revealed = False
    while True:
        command, req = connection.recv()
        if command == 'close':
            break
        if command == 'measure' and not revealed:
            connection.send(seal(dict(request_digest=req['digest'], axis_values=req['axis_values'],
                                      observed=value(req['axis_values']), provenance='SYNTHETIC_PROCESS_WORLD')))
        elif command == 'holdout' and not revealed:
            revealed = True
            connection.send(seal(dict(request_digest=req['digest'], dataset=holdout,
                                      provenance='SYNTHETIC_RESERVED_HOLDOUT')))
        else:
            connection.send({'error': 'world closed after final reveal'})
    connection.close()


class ProcessWorld:
    def __init__(self, seed=42, mode='signal'):
        ctx = mp.get_context('spawn')
        self.connection, remote = ctx.Pipe()
        self.process = ctx.Process(target=_world, args=(remote, seed, mode))
        self.process.start()
        remote.close()
        opening = self._receive()
        self.initial = opening['dataset']
        self.holdout_digest = opening['holdout_dataset_digest']

    def _receive(self):
        if not self.connection.poll(60):
            raise TimeoutError('measurement world did not respond')
        row = self.connection.recv()
        if 'error' in row:
            raise ValueError(row['error'])
        return row

    def measure(self, request):
        self.connection.send(('measure', request))
        return self._receive()

    def reveal_holdout(self, request):
        self.connection.send(('holdout', request))
        return self._receive()

    def close(self):
        if self.process.is_alive():
            self.connection.send(('close', {}))
        self.process.join(5)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join()
        self.connection.close()


def run(seed=42, mode='signal', budget=3):
    world = ProcessWorld(seed, mode)
    try:
        return ClosedLoopResearchOwner().run(dict(dataset=deepcopy(world.initial), seed=0,
                                                 holdout_dataset_digest=world.holdout_digest,
                                                 validation_regime_ids=['VALIDATION'],
                                                 measurement_budget=budget,
                                                 final_nrmse_tolerance=0.25), world)
    finally:
        world.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for seed, mode in [(42,'signal'), (113,'signal'), (271,'signal'), (42,'noise'), (42,'shift')]:
        receipt = run(seed, mode)
        row = dict(seed=seed, mode=mode, receipt=receipt)
        rows.append(row)
        print(json.dumps(dict(seed=seed, mode=mode, status=receipt['status'],
                              rounds=len(receipt['rounds']),
                              nrmse=receipt['final_evaluation'].get('augmented_nrmse')), ensure_ascii=False),flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(seal({'kind':'SYNTHETIC_CAPABILITY_CONTROL', 'runs':rows}),
                                      ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
