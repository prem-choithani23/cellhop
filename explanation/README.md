# CellHop Planner — Visual Explanation Guide

This folder turns a difficult wireless-communications project into a more understandable, presentation-friendly guide.

> The big question is simple:
>
> Which cluster size N should an 84-cell, 300-channel network use so that it can serve many users while keeping interference, fading, and jamming under control?

---

## The project in one picture

```mermaid
flowchart LR
    A[Limited radio spectrum] --> B[Frequency reuse]
    B --> C[Interference analysis]
    A --> D[Channel capacity]
    D --> E[Trunking / Erlang-B]
    A --> F[Propagation effects]
    F --> G[Multipath + delay spread]
    F --> H[Path loss + shadowing + fading]
    A --> I[FHSS / anti-jamming]
    B --> J[Integrated planner]
    C --> J
    E --> J
    G --> J
    H --> J
    I --> J
    J --> K[Recommended cluster size N]
```

---

## Why this problem matters

A cellular network has a limited amount of radio spectrum. If the same frequency is reused too often, nearby cells interfere with each other. If it is reused too little, the network wastes spectrum and cannot serve as many users.

So the design must balance:

- Capacity: how many users can be served
- Interference: how much signal from other cells leaks in
- Reliability: how often the channel becomes weak or distorted
- Robustness: how well the system survives noise and jamming

This project combines all four into one design study.

---

## The six building blocks of the project

| Step | Topic | Why it matters |
|---|---|---|
| 1 | Frequency reuse | decides how often the same spectrum can be reused |
| 2 | Trunking / Erlang-B | tells how many users can be supported without too much blocking |
| 3 | Multipath delay spread | explains whether the channel is strongly distorted |
| 4 | Fading and Doppler | explains signal fluctuations with distance and motion |
| 5 | FHSS and jamming | shows how hopping helps resist interference |
| 6 | Integrated planner | combines them all into one final design choice |

---

## How the project flows

```mermaid
sequenceDiagram
    participant User
    participant Main as main.py
    participant Settings as config/settings.py
    participant Exp1 as exp1_frequency_reuse
    participant Exp2 as exp2_trunking_gos
    participant Exp3 as exp3_multipath
    participant Exp4 as exp4_fading
    participant Exp5 as exp5_fhss
    participant Planner as integrated_planner
    participant Output as outputs/

    User->>Main: Run project
    Main->>Settings: Load design parameters
    Main->>Exp1: Run reuse + interference study
    Main->>Exp2: Run trunking + capacity study
    Main->>Exp3: Run multipath + delay-spread study
    Main->>Exp4: Run fading + mobility study
    Main->>Exp5: Run FHSS + jammer study
    Main->>Planner: Combine all results
    Planner-->>Main: Best cluster size N
    Main->>Output: Save figures, tables, and report
```

---

## Very short presentation version

> This project studies how to design a cellular wireless network under realistic constraints. It combines frequency reuse, capacity analysis, fading, propagation delay, and frequency-hopping spread spectrum to decide the best cluster size for the system. The goal is to maximize the number of users the network can support while keeping interference, signal degradation, and jamming under acceptable limits.

---

## Topic guide

- [01_frequency_reuse.md](./01_frequency_reuse.md)
- [02_trunking_erlang.md](./02_trunking_erlang.md)
- [03_multipath_delay_spread.md](./03_multipath_delay_spread.md)
- [04_fading_and_doppler.md](./04_fading_and_doppler.md)
- [05_fhss_and_jamming.md](./05_fhss_and_jamming.md)
- [06_integrated_planner.md](./06_integrated_planner.md)

---

## Presentation tip

If you are presenting in front of a class, start with this sentence:

> “This project is about designing a wireless cellular network that is both high-capacity and reliable.”

Then explain that the project does not look at a single formula; it combines several wireless-engineering ideas to answer one real design question.

