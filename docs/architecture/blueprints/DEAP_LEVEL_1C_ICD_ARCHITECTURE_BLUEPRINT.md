# Solution Blueprint: Level 1C Interface Control Documents (ICD) & Signal Flow Dictionaries in the DEAP MBSE Compiler

---

## 1. Executive Summary & Systems Engineering Rationale

In classical and digital Model-Based Systems Engineering (MBSE) governed by **ISO/IEC/IEEE 15288:2023** (§6.4.4 *Architecture Definition*, §6.4.5 *Design Definition*, and §6.4.8 *Integration Process*), **IEEE 1362-1998 (R2007)**, and the **INCOSE Systems Engineering Handbook v5**, system specification requires an unbroken digital thread spanning three distinct conceptual layers before decomposing into low-level Agile software artifacts:

```mermaid
flowchart TD
    subgraph "Level 1A: Problem & Purpose Domain (IEEE 1362)"
        L1A["MISSION_INTENT.md\n- Mission Objectives & Primary Roles\n- Environmental & Operational Envelopes\n- Key Performance Parameters (KOPP / MOE)\n- Regulatory Safety Intent"]
    end

    subgraph "Level 1B: Solution Operational Domain (IEEE 1362)"
        L1B["CONOPS.md\n- Multi-Segment System Operational Architecture\n- 8-Phase Operational Flight Lifecycle & Stateflow\n- RF Friis Link Budgets & Dynamic Performance\n- Dual-Tablet HMI & Cognitive Workload (NASA-TLX)\n- Standardized Operating Procedures (SOP-01 to SOP-15)"]
    end

    subgraph "Level 1C: Structural Interface & Data Domain (INCOSE / IEEE 15288) [NEW]"
        L1C["Interface Control Documents (ICD Suite)\n- Inter-Subsystem N² Interface Matrix (ICD-01)\n- Master Signal & Data Flow Dictionary (ICD-02)\n- Bus Protocols, Framing & Opcodes (ICD-03)\n- Physical Connectors, Voltages & Pinouts (ICD-04)"]
    end

    subgraph "Level 2: Agile Requirements & Detailed Design (UML OOA/OOD)"
        L2["docs/epics/ (Subsystems & Part Defs)\ndocs/features/ (Components & Logical UI)\ndocs/user-stories/ (Behavior & BDD Scenarios)\ndocs/use-cases/ (Interactions & Actor Flows)"]
    end

    subgraph "Level 3: Implementation, Autocode & Verification"
        L3["Embedded Source Code (Dart, React, C, SPARK Ada)\nMATLAB / Simulink / Stateflow Dynamic Models\nContinuous Headless Digital Twin Execution"]
    end

    L1A -->|Defines Purpose & Envelopes for| L1B
    L1B -->|Allocates Operational Topology to| L1C
    L1C -->|Defines Port Contracts & Signals for| L2
    L2 -->|Synthesizes Source & Models in| L3
```

### The Architectural Problem Solved
Currently, the DEAP pipeline jumps directly from Level 1B (`docs/conops/CONOPS.md`) to Level 2 (`docs/epics/`, `docs/features/`). This omission causes:
1. **Architectural Contamination & Boundary Breaches**: Low-level hardware pinouts, baud rates, CRC polynomials, and cable routing leak into high-level concept documents (`MISSION_INTENT.md` or `CONOPS.md`).
2. **Fragmented Interface Contracts**: Port names, signal rates, and data dictionaries are scattered across dozens of individual Feature files (`docs/features/feat-XXX.md`) without a single authoritative system-level interface contract.
3. **Implicit Dataflow & Timing**: Signal update rates ($f$ Hz), quantization/resolution, fault values, and latency tolerances ($\tau_{max}$ ms) are buried inside code or ASTs without a formal ICD contract.

---

## 2. Abstract Schema AST to ICD Metamodel Mapping

In strict adherence to the **Pure Schema-Driven Compiler Invariant (Zero Hardcoded Domain Concepts)**, the DEAP compiler ingests input schemas (`*.sysml`, `*.yang`, `*.proto`, `*.arxml`, `*.idl`) and maps abstract AST nodes into the formal ICD metamodel:

```mermaid
classDiagram
    class SchemaAST_Root {
        +List~PackageNode~ packages
        +List~PartDefNode~ part_defs
        +List~PortDefNode~ port_defs
        +List~InterfaceDefNode~ interface_defs
        +List~ConnectionNode~ connections
        +List~ItemFlowNode~ item_flows
    }

    class ICD_SystemInterfaceMatrix {
        +Matrix~Subsystem, Subsystem~ n2_matrix
        +List~InterfaceLink~ physical_links
        +List~InterfaceLink~ logical_links
    }

    class ICD_SignalDictionary {
        +String signal_id
        +String signal_name
        +String source_port
        +String destination_port
        +String data_type
        +String engineering_unit
        +Float min_value
        +Float max_value
        +Float update_rate_hz
        +Float quantization_resolution
        +String fault_default_value
        +Float latency_tolerance_ms
    }

    class ICD_ProtocolContract {
        +String bus_name
        +String physical_layer
        +String data_link_framing
        +String checksum_crc_poly
        +Integer baud_rate_bps
        +List~OpcodeDefinition~ opcodes
    }

    class ICD_PhysicalConnector {
        +String connector_id
        +String part_number
        +Integer pin_count
        +List~PinMapping~ pin_assignments
        +Float nominal_voltage_v
        +Float voltage_min_v
        +Float voltage_max_v
        +Float max_current_amps
    }

    SchemaAST_Root --> ICD_SystemInterfaceMatrix : compiles to
    SchemaAST_Root --> ICD_SignalDictionary : extracts item_flows
    SchemaAST_Root --> ICD_ProtocolContract : extracts interface_defs
    SchemaAST_Root --> ICD_PhysicalConnector : extracts physical port_defs
```

### Transformation Rules:
1. **Subsystems ($S_1, \dots, S_k$)**: Derived from top-level `package` or `part def` nodes representing major architectural segments.
2. **Ports & Directionality**: Derived from `port def` declarations with `in`, `out`, or `inout` flow properties.
3. **Connections & Topologies**: Derived from `connection` and `interface def` blocks linking `port_A` to `port_B`.
4. **Signals & Data Types**: Derived from `item flow` and `item def` declarations, capturing structured payloads, numeric ranges, and update frequencies.
5. **Protocol & Electrical Invariants**: Derived from typed port properties, attributes, and constraints (`baudRate`, `crcPolynomial`, `voltageNominal`).

---

## 3. Standardized Level 1C ICD Suite Specification (`docs/interfaces/`)

The generated ICD suite resides in `docs/interfaces/` (or `docs/icd/`) and consists of four standard specification documents:

```
docs/interfaces/
├── ICD_01_SYSTEM_INTERFACE_MATRIX.md   # Platform N² Matrix & Inter-Subsystem Topology
├── ICD_02_MASTER_SIGNAL_DICTIONARY.md  # Master Signal & Telemetry Data Dictionary
├── ICD_03_BUS_PROTOCOLS.md             # Framing, CRC, Opcode & Timing Contracts
└── ICD_04_PHYSICAL_CONNECTORS.md       # Pinouts, Voltages, Grounding & Wire Harnesses
```

### 3.1 ICD-01: System Interface & $N^2$ Matrix Specification
- **System Connectivity Graph**: Mermaid `flowchart` or `graph TD` representing all physical and logical inter-subsystem interfaces.
- **Subsystem $N^2$ Matrix**: The canonical systems engineering square matrix where diagonal elements represent subsystems $S_1..S_k$, and off-diagonal cells $(i, j)$ define the unidirectional interface from $S_i$ to $S_j$.
- **Interface Categorization**: Physical Energy Links (High Voltage, 24V DC, 5V Logic), Discrete Signal Lines (PWM, Interlocks, IRQ), Digital Buses (RS-485, CAN, Ethernet, SPI, I2C), and Wireless RF Datalinks (FHSS, Remote ID, ADS-B).

### 3.2 ICD-02: Master Signal & Data Flow Dictionary
Every signal traversing an inter-subsystem boundary is cataloged in a standardized, machine-verifiable table:

| Signal ID | Signal Name | Source Subsystem | Destination Subsystem | Data Type | Engineering Units | Valid Range $[min, max]$ | Update Rate ($f$ Hz) | Resolution | Fault / Safe Value | Latency Ceiling ($\tau_{max}$) | Source Citation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `SIG-ESD-001` | `ArmState` | ESAD Subsystem | Flight Control Computer | `uint8` | enum (`0x00`..`0x05`) | `[0, 5]` | 100 Hz | 1 state | `0x00` (SAFE) | 10 ms | `schema/extracted/ESAD_ICD_full.md#L626` |
| `SIG-PMU-002` | `BusVoltage` | Power Management Unit | Flight Control Computer | `float32` | Volts ($V$) | `[14.0, 32.0]` | 50 Hz | 0.01 V | 0.0 V | 20 ms | `schema/extracted/ESAD_ICD_full.md#L315` |
| `SIG-NAV-003` | `Airspeed_IAS`| Pitot-Static Sensor | Flight Control Computer | `float32` | $\text{m/s}$ | `[0.0, 80.0]` | 50 Hz | 0.05 m/s | 0.0 m/s | 20 ms | `schema/extracted/A5_user_manual_full.md#L384` |

### 3.3 ICD-03: Bus Protocols, Framing & Opcodes
- **Physical & Data Link Layers**: Baud rates, bit timing, line termination ($\Omega$), differential signaling levels, and half/full-duplex topology.
- **Packet Structure & Framing**: Header delimiters, Message Length field, Opcode/Command field, Payload bytes, and Error Detection (e.g. CRC-16 XModem: polynomial $0x1021$, initial value $0x0000$).
- **Opcode & Command Catalog**: Complete enumeration of command numbers, request payloads, response payloads, execution timeouts, and error response codes.
- **Bus Timing & Arbitration**: Polling periods, master/slave query-response windows, collision avoidance, and bus timeout watchdog behavior.

### 3.4 ICD-04: Physical Connectors & Electrical Boundaries
- **Connector Allocation Matrix**: Standardized hardware connectors (e.g. ODU, Harwin, Molex, N-Type, SMA), mating part numbers, backshell shielding, and retention mechanisms (e.g. zero-retention detent $< 15.0\text{ N}$).
- **Pin Assignment Tables**: Pin number, signal name, wire gauge (AWG), signal type (Power, Ground, RS-485 A/B, Discrete In, Shield).
- **Electrical Envelope Invariants**: Nominal voltage, minimum voltage, maximum overvoltage clamp, continuous current rating, peak transient current, and ESD protection rating (e.g. MIL-STD-461 / IEC 61000-4-2).

---

## 4. Pipeline Integration & Orchestrator Lifecycle

We incorporate the ICD Engineering phase cleanly into the **Autonomous Specification Orchestrator (`skills/spec-orchestrator/SKILL.md`)**:

```mermaid
sequenceDiagram
    autonumber
    participant COORD as "Master Orchestrator (Coordinator)"
    participant W0 as "Phase 0: Schema Ingestion (SysML v2 / YANG)"
    participant W1 as "Phase 1: Structural Worker (Epics & Features)"
    participant W_ICD as "Phase 1.5: Interface Spec Worker (ICD Suite) [NEW]"
    participant W2 as "Phase 2: Behavioral Worker (User Stories)"
    participant W3 as "Phase 3: System Interaction Worker (Use Cases)"
    participant VAL as "Phase 4: Parity Auditor & ICD Linter"

    COORD->>W0: Ingest Schemas (.pipeline/schema.sysml)
    COORD->>W1: Dispatch Structural Worker (Epics & Features)
    W1-->>COORD: Features Created & Registered in Tracker
    
    Note over COORD,W_ICD: "Phase 1.5: Interface Extraction & ICD Engineering"
    COORD->>W_ICD: Dispatch Interface Spec Worker (schema.sysml AST)
    W_ICD->>W_ICD: Compile ICD-01 N² Matrix & ICD-02 Signal Dictionary
    W_ICD->>W_ICD: Compile ICD-03 Protocol Framing & ICD-04 Connector Pinouts
    W_ICD-->>COORD: Register ICD Suite (docs/interfaces/ & tracker)
    
    COORD->>W2: Dispatch Behavioral Worker (User Stories with Port Contracts)
    COORD->>W3: Dispatch Interaction Worker (Use Cases)
    COORD->>VAL: Execute 23 Parity Gates (including ICD Validator Gate 23)
    VAL-->>COORD: 100% Schema & Interface Parity Verified
```

### New Phase 1.5 Specification:
- **Phase 1.5: Interface & ICD Extraction (Worker ICD)**:
  1. **Trigger**: Invoked following Phase 1 completion with `spec-icd-engineering` skill and path to `.pipeline/schema.sysml`.
  2. **Execution**: Parses `port def`, `interface def`, `connection`, and `item flow` AST nodes. Generates `docs/interfaces/ICD_01_SYSTEM_INTERFACE_MATRIX.md`, `ICD_02_MASTER_SIGNAL_DICTIONARY.md`, `ICD_03_BUS_PROTOCOLS.md`, and `ICD_04_PHYSICAL_CONNECTORS.md`.
  3. **Verification**: Executes `parity_auditor/validators/icd_validator.py` asserting:
     - *Zero Dangling Ports*: Every output port connects to a valid input port.
     - *Signal Parity*: 100% of `item flow` types in SysML AST are cataloged in the Master Signal Dictionary.
     - *Type & Rate Safety*: Port data types and update rates match between connected components.
     - *Tracker Synchronization*: Registers the ICD suite under the `icd` issue label.

---

## 5. Parity Auditor Gate 23: ICD & Signal Flow Completeness Validator

A new automated verification gate (`Gate 23`) is added to `skills/spec-orchestrator/parity_auditor/`:

```python
class ICDCompletenessValidator(BaseValidator):
    """Mechanically verifies that all subsystem interfaces, ports, and signal flows
    in the SysML v2 AST are 100% reflected in docs/interfaces/ ICD suite."""
    
    def validate(self, repo: Path) -> List[Finding]:
        findings = []
        # 1. Verify docs/interfaces/ suite exists and contains ICD-01..04
        # 2. Extract all 'port def' and 'connection' nodes from schema AST
        # 3. Assert every AST connection is represented in ICD-01 N² matrix
        # 4. Assert every AST item flow is defined in ICD-02 Signal Dictionary
        # 5. Assert bus protocols in ICD-03 define physical layer, baud, and CRC
        # 6. Assert connector pinouts in ICD-04 have zero unassigned active pins
        return findings
```

---

## 6. Concrete Downstream Instantiation: Avenger 5 (`uas-003`)

In the downstream customer repository (`uas-003`), the missing ICD layer is instantiated directly from the Level 0 OEM extraction corpus (`schema/extracted/`):

```mermaid
flowchart LR
    subgraph GCS ["GCS Segment"]
        GCS_BOX["Ground BOX\n(24V DC / LAN)"]
        RADIO_BOX["Radio BOX\n(4.4-5.0 GHz FHSS)"]
    end

    subgraph LAU ["Launch Segment"]
        PL40["PL-40 Catapult\n(13-14 bar)"]
        UMB["12-Pin Ventral Umbilical\n(F_pull < 15 N)"]
    end

    subgraph AVIONICS ["Airborne Avionics Segment"]
        PMU["28V PMU\n(12S LiPo 49-50V)"]
        FCC["Dual FCCs\n(EKF / L1 / TECS)"]
    end

    subgraph SEEKER ["Payload Segment"]
        GIMBAL["2-Axis Gimbal\n(HD EO/IR)"]
    end

    subgraph LETHALITY ["Lethality Segment"]
        ESAD["STANAG 4187 ESAD\n(100 Hz RS-485)"]
        PROX["Proximity / Impact Sensor"]
        LEEFI["LEEFI High-Voltage Detonator"]
    end

    GCS_BOX <-->|"15m Tactical Ethernet"| RADIO_BOX
    RADIO_BOX <===>|"4.4-5.0 GHz FHSS Datalink (ICD-03)"| FCC
    UMB -.-|"24V DC Ground Power (ICD-04)"| PMU
    PMU -->|"28V DC Regulated Bus (ICD-04)"| FCC
    PMU -->|"28V DC via J100 Pin 1-2 (ICD-04)"| ESAD
    FCC <-->|"100 Hz RS-485 Bus (Opcodes 0x10/0x11/0x12/0x13) (ICD-03)"| ESAD
    FCC -->|"DSC_IN1 1 kHz 50% PWM Arm Enable (ICD-03)"| ESAD
    PROX -->|"IRQ_L Trigger via J102 (ICD-04)"| ESAD
    ESAD -->|"High-Voltage Discharge via J401 (ICD-04)"| LEEFI
    FCC <-->|"250 Hz SPI / Serial Seeker Control (ICD-02)"| GIMBAL
```

### Concrete Deliverables for `uas-003`:
1. `docs/interfaces/ICD_01_SYSTEM_INTERFACE_MATRIX.md`: 5x5 $N^2$ matrix mapping GCS, Launch, Avionics, Seeker, and ESAD.
2. `docs/interfaces/ICD_02_MASTER_SIGNAL_DICTIONARY.md`: Complete dictionary of all 42 internal signals (pitot dynamic pressure, EKF state vector, gimbal angles, battery voltage/current, ESAD arm state).
3. `docs/interfaces/ICD_03_BUS_PROTOCOLS.md`: RS-485 half-duplex 115200 8N1 framing, CRC-16 XModem ($0x1021$), Opcodes `0x10` (EXCHANGE), `0x11` (PBIT), `0x12` (HIGHVOLTAGE), `0x13` (VERSION), `0xB0` (WELCOME), and 1 kHz 50% PWM `DSC_IN1`.
4. `docs/interfaces/ICD_04_PHYSICAL_CONNECTORS.md`: Pinouts for J100 (16-pin system), J102 (10-pin sensor), J401 (high-voltage LEEFI), and 12-pin ventral umbilical.

---

## 7. Polyrepo Rollout & Roadmap

1. **Step 1: Codify Abstract ICD Governance in `DEAP-spec-core`**:
   - Add Standard 13 (*Interface Control Documents & Signal Flow Dictionaries*) to `rules/systems-engineering-standards.md`.
   - Update `skills/spec-orchestrator/SKILL.md` with Phase 1.5.
   - Implement `ICDCompletenessValidator` (Gate 23) in Parity Auditor.
2. **Step 2: Instantiate Concrete ICD Suite in `uas-003`**:
   - Synthesize `docs/interfaces/` suite for Avenger 5 from `schema/extracted/`.
3. **Step 3: Distribute & Verify Across All 7 Repositories**:
   - Run unit test suites, baseline checks, and remote sync verification.
