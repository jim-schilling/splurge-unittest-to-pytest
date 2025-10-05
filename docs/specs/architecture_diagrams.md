    
    F --> J{Recoverable?}
    G --> J
    H --> J
    I --> J

    J -->|Yes| K[Continue with Warning]
    J -->|No| L[Fail Pipeline]

    K --> C
    L --> M[Generate Error Report]
    M --> N[End Pipeline]
```

## Configuration and Extension Points

```mermaid
graph LR
    A[User Config] --> B[Config Manager]
    B --> C[Pipeline Builder]
    C --> D[Core Steps]
    C --> E[Plugin Steps]
    C --> F[Custom Rules]

    B --> Z[Configuration Validator]
    B --> Y[Suggestion Engine]
    B --> X[Template Manager]

    G[Plugin System] --> E
    H[Custom Transformations] --> F

    subgraph "Extension Points"
        E
        F
        I[Event Handlers]
        J[Output Formatters]
    end

    G --> I
    G --> J
```

## Memory and Performance Model

```mermaid
graph TD
    A[File Input] --> B[Streaming Parser]
    B --> C[AST Cache]
    C --> D[Pattern Cache]
    D --> E[IR Generation]
    E --> F[Code Generation]
    F --> G[Output Buffer]
    G --> H[File Output]
    
    subgraph "Memory Management"
        I[GC Triggers]
        J[Cache Limits]
        K[Stream Processing]
    end
    
    C --> I
    D --> J
    B --> K
```

## Deployment Architecture

```mermaid
graph TB
    A[GitHub Repository] --> B[CI/CD Pipeline]
    B --> C[Test Suite]
    B --> D[Performance Tests]
    B --> E[Security Scan]
    
    C --> F{All Tests Pass?}
    D --> F
    E --> F
    
    F -->|Yes| G[Build Artifacts]
    F -->|No| H[Fail Build]
    
    G --> I[PyPI Package]
    G --> J[Docker Image]
    G --> K[Standalone Binary]
    
    subgraph "Distribution Channels"
        I
        J
        K
        L[GitHub Releases]
    end

    Note[Note] --> M[Automated Releases]
    
    G --> L
```

## Component Interaction Details

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Config
    participant Pipeline
    participant EventBus
    participant Steps
    participant FileSystem
    
    User->>CLI: unittest-to-pytest migrate
    CLI->>Config: load_config()
    Config-->>CLI: MigrationConfig
    
    CLI->>Pipeline: create_pipeline(config)
    Pipeline->>EventBus: register_subscribers()
    
    CLI->>Pipeline: migrate_files(file_list)
    
    loop for each file
        Pipeline->>EventBus: publish(FileStartedEvent)
        Pipeline->>Steps: execute_parse_job()
        Steps->>FileSystem: read_file()
        FileSystem-->>Steps: source_code
        Steps->>EventBus: publish(StepCompletedEvent)
        
        Pipeline->>Steps: execute_transform_job()
        Steps->>EventBus: publish(StepCompletedEvent)

        Pipeline->>Steps: execute_generate_job()
        Steps->>EventBus: publish(StepCompletedEvent)

        Pipeline->>Steps: execute_format_job()
        Steps->>EventBus: publish(StepCompletedEvent)

        Pipeline->>Steps: execute_output_job()
        Steps->>FileSystem: write_file()
        Steps->>EventBus: publish(StepCompletedEvent)

        Pipeline->>EventBus: publish(FileCompletedEvent)
    end
    
    Pipeline-->>CLI: MigrationResult
    CLI-->>User: Summary Report
```

### EventBus sequence (overview)

```mermaid
sequenceDiagram
    participant CLI
    participant Pipeline
    participant EventBus
    participant Subscriber

    CLI->>Pipeline: migrate(files)
    Pipeline->>EventBus: publish(file.migrate.started)
    EventBus->>Subscriber: notify
    Pipeline->>EventBus: publish(step.completed)
    EventBus->>Subscriber: notify
    Pipeline->>EventBus: publish(file.migrate.completed)
    EventBus->>Subscriber: notify
``` 

### Common events and payloads

- `file.migrate.started`: {source, timestamp, run_id}
- `file.migrate.completed`: {source, target?, wrote, duration_s, run_id}
- `step.started`: {step, source, timestamp}
- `step.completed`: {step, source, duration_s, status, metadata}
- `error.reported`: {category, location?, message, suggestions}

![Event sequence diagram](../assets/event_sequence.svg)

Figure: EventBus sequence (SVG fallback contains mermaid source). Use a mermaid-aware viewer to render dynamically.


## Data Transformation Pipeline

```mermaid
flowchart TB
    subgraph "Input Processing"
        A[unittest Source] --> B[libcst Parse]
        B --> C[Syntax Tree]
    end
    
    subgraph "Pattern Recognition"
        C --> D[TestCase Scanner]
        C --> E[Method Scanner]
        C --> F[Assertion Scanner]
        C --> G[Import Scanner]
        
        D --> H[Class Patterns]
        E --> I[Method Patterns]
        F --> J[Assertion Patterns]
        G --> K[Import Patterns]
    end
    
    subgraph "IR Generation"
        H --> L[TestClass IR]
        I --> M[TestMethod IR]
        J --> N[Assertion IR]
        K --> O[Import IR]
        
        L --> P[TestModule IR]
        M --> P
        N --> P
        O --> P
    end
    
    subgraph "Code Generation"
        P --> Q[Fixture Generator]
        P --> R[Test Function Generator]
        P --> S[Assertion Generator]
        P --> T[Import Generator]
        
        Q --> U[pytest Fixtures]
        R --> V[pytest Functions]
        S --> W[pytest Assertions]
        T --> X[pytest Imports]
    end
    
    subgraph "Output Assembly"
        U --> Y[Code Assembler]
        V --> Y
        W --> Y
        X --> Y

        Y --> Z[Raw pytest Code]
    end

    subgraph "Final Formatting"
        Z --> AA[isort API]
        AA --> BB[Import Sorting]
        BB --> CC[black API]
        CC --> DD[Code Formatting]
        DD --> EE[Formatted pytest Code]
    end
```

## Plugin Architecture

```mermaid
classDiagram
    class PluginManager {
        +plugins: List[Plugin]
        +load_plugins()
        +register_plugin(plugin)
        +get_steps() List[Step]
        +get_handlers() Dict[Type, Callable]
    }
    
    class Plugin {
        <<interface>>
        +name: str
        +version: str
        +get_steps() List[Step]
        +get_event_handlers() Dict[Type, Callable]
        +configure(config) None
    }
    
    class CustomAssertionPlugin {
        +name: "custom_assertions"
        +get_steps() List[Step]
        +get_event_handlers() Dict[Type, Callable]
    }
    
    class MockTransformPlugin {
        +name: "mock_transform"
        +get_steps() List[Step]
        +get_event_handlers() Dict[Type, Callable]
    }
    
    class CustomStep~T,R~ {
        +plugin_name: str
        +execute(context, input) Result~R~
    }
    
    PluginManager *-- Plugin
    Plugin <|.. CustomAssertionPlugin
    Plugin <|.. MockTransformPlugin
    Plugin *-- CustomStep
```

## Error Recovery Strategies

```mermaid
flowchart TD
    A[Error Detected] --> B{Error Category}
    
    B -->|Parse Error| C[Syntax Recovery]
    B -->|Pattern Error| D[Pattern Fallback]
    B -->|IR Error| E[IR Repair]
    B -->|Generation Error| F[Minimal Generation]
    B -->|IO Error| G[File Handling]
    
    C --> C1[Try Encoding Fix]
    C --> C2[Try Syntax Repair]
    C --> C3[Skip Malformed Sections]
    
    D --> D1[Use Generic Pattern]
    D --> D2[Skip Unknown Pattern]
    D --> D3[Manual Intervention Flag]
    
    E --> E1[Validate IR Structure]
    E --> E2[Fix Missing Dependencies]
    E --> E3[Generate Minimal IR]
    
    F --> F1[Basic Test Structure]
    F --> F2[Preserve Original Logic]
    F --> F3[Add TODO Comments]
    
    G --> G1[Retry with Backoff]
    G --> G2[Change File Permissions]
    G --> G3[Use Temp Files]
    
    C1 --> H{Success?}
    C2 --> H
    C3 --> H
    D1 --> H
    D2 --> H
    D3 --> H
    E1 --> H
    E2 --> H
    E3 --> H
    F1 --> H
    F2 --> H
    F3 --> H
    G1 --> H
    G2 --> H
    G3 --> H
    
    H -->|Yes| I[Continue Pipeline]
    H -->|No| J[Log Error & Continue]
    
    I --> K[Success with Warning]
    J --> L[Partial Failure]
```

## Testing Strategy Architecture

```mermaid
graph TB
    subgraph "Unit Tests"
        A[Step Tests]
        B[Task Tests]
        C[Job Tests]
        D[Utility Tests]
    end
    
    subgraph "Integration Tests"
        E[Pipeline Tests]
        F[End-to-End Tests]
        G[Performance Tests]
    end
    
    subgraph "Property Tests"
        H[Transformation Correctness]
        I[Round-trip Validation]
        J[Error Handling]
    end
    
    subgraph "Regression Tests"
        K[Real-world Samples]
        L[Edge Cases]
        M[Previous Bugs]
    end
    
    subgraph "Dogfooding"
        N[Self Migration]
        O[Continuous Validation]
        P[Quality Metrics]
    end
    
    A --> Q[Test Suite]
    B --> Q
    C --> Q
    D --> Q
    E --> Q
    F --> Q
    G --> Q
    H --> Q
    I --> Q
    J --> Q
    K --> Q
    L --> Q
    M --> Q
    N --> Q
    O --> Q
    P --> Q
    
    Q --> R[CI/CD Pipeline]
    R --> S[Quality Gates]
    S --> T[Release Decision]
```
