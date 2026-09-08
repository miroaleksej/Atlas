# Φ-Compiler PHI-RLC-HRC-01
## Физический низковольтный стенд CURRENT-STATE v2.4

Этот документ является полной активной спецификацией первого физического стенда Φ-Compiler. Он не является отчётом о проведённом измерении. До подключения реального прибора статусы `REAL_DEVICE`, `MEASURED_COVARIANCE`, `HARDWARE_ESTOP` и `PRIVATE_GUARDED_REENTRY` остаются `NOT_RUN`.

## 1. Назначение

Стенд предназначен для проверки, может ли Φ-Compiler по слепым измерениям входа и одного наблюдаемого состояния:

1. обнаружить конечномерную скрытую память;
2. восстановить класс `H23_EXP_MEMORY_EQUIV`, не разделяя наблюдательно эквивалентные H2 и H3;
3. оценить measured covariance и latency;
4. обнаружить внесённый bounded drift;
5. скомпилировать контроллер и наблюдатель офлайн;
6. допустить guarded reentry только после отдельного real-time backend и private measured validation.

## 2. Единственная активная топология

```text
Red Pitaya OUT1
     │
    K1A   fail-open relay contact
     │
  RPROT 100 Ω
     │
  RSOURCE 50 Ω (эквивалент выходного сопротивления прибора)
     │
  L1 10 mH + measured DCR ≈ 30 Ω
     │  node H
     ├──────── RH 1.00 kΩ ────────┐
     └──────── CH 220 nF ─────────┤
                                  │ node X
                               C1 100 nF
                                  │
                                 GND
```

Измерения:

```text
IN1 ← 100 kΩ / 100 kΩ divider ← фактический OUT1
IN2 ← 100 kΩ / 100 kΩ divider ← node X = voltage on C1
```

Оба fast input переключателя устанавливаются в LV. IN1 и IN2 имеют общий ground с OUT1. Стенд не подключается к сети, внешнему силовому источнику или другому активному объекту.

## 3. Точное соответствие активной математике

Пусть

- `x = v_C` — напряжение на основном конденсаторе `C1`;
- `q = C x` — заряд `C1`;
- `i = dq/dt = C dx/dt` — ток последовательной цепи;
- `z` — напряжение на скрытом элементе `RH || CH`;
- `R = RSOURCE + RPROT + DCR(L1)`.

Для параллельного скрытого элемента:

\[
i=\frac{z}{R_h}+C_h\dot z,
\]

поэтому

\[
\dot z=-\frac{1}{R_hC_h}z+\frac{C}{C_h}\dot x.
\]

KVL всей последовательной цепи:

\[
L\ddot q+R\dot q+z+x=u.
\]

После подстановки `q=Cx`:

\[
\boxed{
\ddot x+\frac{R}{L}\dot x+\frac{1}{LC}x+\frac{1}{LC}z
=\frac{1}{LC}u
}
\]

\[
\boxed{
\dot z=-\frac{1}{R_hC_h}z+\frac{C}{C_h}\dot x
}
\]

Это не приближённая аналогия, а точная lumped-element realization активной `ResonatorStateModel` в пределах линейной RLC-модели компонентов.

Для номиналов revision A:

| Параметр | Значение |
|---|---:|
| `R` | 180 Ω |
| `L` | 10 mH |
| `C` | 100 nF |
| `Rh` | 1.00 kΩ |
| `Ch` | 220 nF |
| `1/(LC)` | 1.0×10⁹ s⁻² |
| `R/L` | 1.8×10⁴ s⁻¹ |
| `1/(Rh Ch)` | 4.545×10³ s⁻¹ |
| `C/Ch` | 0.454545 |
| ideal `f0` | 5.033 kHz |
| normalization time `sqrt(LC)` | 31.623 µs |

В dimensionless recovery coordinates `τ=t/sqrt(LC)` номинальная модель имеет порядок единицы, что сохраняет текущие bounds recovery-owner без введения отдельного упрощённого восстановителя.

## 4. Предварительно сертифицированное возбуждение

```text
start delay       0.500 ms
pulse 1           +0.080 V, 0.800 ms
wait              1.000 ms
pulse 2           -0.060 V, 0.500 ms
probe              5.000 kHz, fraction 0.18, decay 4.000 ms
observation        20.000 ms
sample rate        488.28125 kS/s (125 MS/s / 256)
```

Operator-approved limits:

| Ограничение | Значение |
|---|---:|
| max absolute drive | 0.25 V |
| max absolute physical response | 0.60 V |
| max RMS response | 0.25 V |
| max response slew | 100 kV/s |
| max excitation energy | 1.0×10⁻⁴ V²·s |
| max observation time | 50 ms |
| minimum sample rate | 250 kS/s |

Номинальный offline prebuild даёт peak response около 0.083 V. Полный deterministic tolerance-box из 512 углов также проходит все gates; наихудший peak response остаётся ниже 0.089 V. Это только расчётный prebuild bound, не measured evidence.

## 5. Fail-open аппаратное отключение

Программная команда `OUTPUT OFF` не считается аппаратным emergency stop.

### 5.1 Силовой путь сигнала

Контакт `K1A` включён последовательно между OUT1 и RPROT. Используется normally-open contact: при отсутствии питания катушки цепь разомкнута.

### 5.2 Катушка

```text
external 5 V low-voltage supply
 → normally-closed ESTOP button
 → K1 coil
 → drain Q1 N-MOSFET
 → source GND
```

- `DIO2_P` → 1 kΩ → gate Q1;
- 100 kΩ от gate к GND обеспечивает default OFF;
- flyback diode включён встречно-параллельно катушке;
- GPIO не питает катушку непосредственно;
- ток катушки выбран не более 60 mA;
- ground внешнего 5 V источника соединён с Red Pitaya ground только в одной точке.

### 5.3 Независимая обратная связь

Вторая группа контактов `K1B` формирует readback:

```text
3.3 V → 10 kΩ → K1B(NO) → DIO3_P
DIO3_P → 100 kΩ → GND
```

`DIO3_P=HIGH` означает физически замкнутый relay contact. `DIO2_P` и `DIO3_P` различны. Перед первым возбуждением adapter обязан доказать последовательность:

```text
OPEN before arm → CLOSED while armed → OPEN after emergency stop
```

Если readback не совпадает с командой, excitation запрещается и выполняется `OUTPUT OFF + relay OFF + ACQ STOP + GEN RST`.

## 6. Wiring checklist до подачи сигнала

1. Red Pitaya выключена; OUT1, IN1 и IN2 не подключены.
2. Омметром подтверждены значения RPROT, RH и всех divider resistors.
3. Измерены L1 и DCR; фактические значения внесены в `PHYSICAL_STAND.json` до квалификации.
4. Проверены C1 и CH; электролитические конденсаторы для C1/CH не используются.
5. Между node X и GND нет внешнего питания.
6. Проверена правильность общей земли.
7. ESTOP размыкает катушку независимо от GPIO.
8. При выключенной Red Pitaya K1A разомкнут.
9. IN1 и IN2 установлены в LV.
10. Делители 2:1 проверены постоянным напряжением не выше 0.2 V.
11. Expected serial прибора записан оператором явно.
12. Выполнена команда `physical-prebuild`; все gates PASS.
13. Только после этого разрешена команда `physical-open-loop --operator-approved`.

## 7. Calibration captures

Требуется не менее 12 синхронных zero-drive captures при подключённом стенде. Для каждого capture сохраняются:

- immutable instrument identity;
- IN1 и IN2 raw arrays;
- sample rate и decimation;
- trigger/acquisition latency;
- relay feedback;
- raw evidence digest.

Владелец `estimate_calibration_package` масштабирует raw ADC values коэффициентом divider gain `2.0`, после чего вычисляет offsets, shrinkage covariance, eigenvalue floor, AR(1) и latency statistics в физических вольтах.

Factory calibration Red Pitaya не заменяет session calibration. Производитель указывает, что offset/gain могут различаться между платами и меняться со временем; для точной работы предусмотрены calibration application/utility.

## 8. Identification captures

После calibration выполняются 10 повторов одного сертифицированного open-loop experiment. IN1 считается фактическим `u(t)`, IN2 — наблюдаемым `x(t)`. Время нормируется:

\[
\tau=\frac{t}{\sqrt{LC}}.
\]

В recovery передаётся один `Episode`, где десять measured trajectories являются replicates. Private truth отсутствует. Результат обязан сохранить единый класс `H23_EXP_MEMORY_EQUIV`; H2 и H3 не разделяются.

## 9. Controller boundary

После model gate разрешена офлайн-компиляция physical-units model и проверка DARE/observer/invariant ellipsoid. Однако network SCPI запрещён как real-time feedback backend для этого 5 kHz стенда.

```text
SCPI generation/acquisition       ALLOWED
SCPI open-loop identification     ALLOWED
SCPI real-time closed-loop        BLOCKED
controller guarded reentry        BLOCKED until deterministic backend
```

Для реального guarded reentry необходим отдельный backend с bounded worst-case cycle time, watchdog, hardware relay control и timestamped state/measurement logs. Он должен пройти private measured validation; digital twin или offline replay не заменяют это испытание.

## 10. Команды

Offline prebuild:

```bash
python -m interfaces.phi_compiler_cli \
  --mode physical-prebuild \
  --contract hardware/PHYSICAL_STAND.json \
  --output reports/phi_physical_prebuild_v2_4.json
```

In-memory relay/adapter contract:

```bash
python -m interfaces.phi_compiler_cli \
  --mode physical-adapter \
  --contract hardware/PHYSICAL_STAND.json \
  --output reports/phi_physical_adapter_contract_v2_4.json
```

Реальный open-loop этап запускается только после ручной проверки схемы:

```bash
python -m interfaces.phi_compiler_cli \
  --mode physical-open-loop \
  --contract hardware/PHYSICAL_STAND.json \
  --host rp-xxxxxx.local \
  --expected-serial ACTUAL_SERIAL \
  --operator-approved \
  --raw-output reports/private/phi_real_raw_v2_4.npz \
  --output reports/private/phi_real_open_loop_v2_4.json
```

Без `--operator-approved`, expected serial или аппаратного relay feedback возбуждение не начинается.

## 11. Источники и hardware limits

- STEMlab 125-14 specifications: https://redpitaya.readthedocs.io/en/latest/developerGuide/hardware/ORIG_GEN/125-14/top.html
- Fast analog inputs: https://redpitaya.readthedocs.io/en/latest/developerGuide/hardware/ORIG_GEN/measurements/STEMlab-125-14/fast_analog_inputs.html
- Fast analog outputs: https://redpitaya.readthedocs.io/en/latest/developerGuide/hardware/ORIG_GEN/measurements/STEMlab-125-14/fast_analog_outputs.html
- Calibration: https://redpitaya.readthedocs.io/en/latest/appsFeatures/systemtool/calibration/calibration.html
- Acquisition commands: https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/command_list/commands-acq.html
- Generator commands: https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/command_list/commands-gen.html
- Digital GPIO commands: https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/command_list/commands-digital.html
- SciPy ZOH discretization: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.cont2discrete.html
- SciPy DARE: https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_discrete_are.html

## 12. Current claim boundary

```text
PHYSICAL_STAND_TOPOLOGY          = COMPLETE_SPEC
PREBUILD_NOMINAL                 = PASS
PREBUILD_TOLERANCE_CORNERS       = 512/512 PASS
RELAY_SCPI_CONTRACT              = 10/10 PASS_IN_MEMORY
HARDWARE_DIGITAL_TWIN            = 20/20 PASS
SYNTHETIC_NON_REGRESSION         = 120/120 EXACT
REAL_INSTRUMENT_IDENTITY         = NOT_READ
MEASURED_CALIBRATION_CAPTURES    = NOT_RUN
MEASURED_COVARIANCE_LATENCY      = NOT_AVAILABLE
HARDWARE_ESTOP_PHYSICAL          = NOT_RUN
REAL_OPEN_LOOP_RECOVERY          = NOT_RUN
REALTIME_CONTROL_BACKEND         = NOT_IMPLEMENTED
PRIVATE_GUARDED_REENTRY          = BLOCKED
TECHNOLOGICAL_BREAKTHROUGH       = NOT_ESTABLISHED
```
