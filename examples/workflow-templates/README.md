# Workflow Templates

This directory contains comprehensive workflow templates for unittest to pytest migration scenarios. Each template provides a structured approach to migration with defined steps, success criteria, and troubleshooting guidance.

## Available Workflow Templates

### `simple-migration-workflow.yaml`
**Purpose**: Basic workflow for single file migrations
**Use Case**: Converting individual test files with standard patterns
**Key Features**:
- 5-step migration process
- Input validation and output verification
- Basic troubleshooting guide
- Success criteria defined

### `comprehensive-migration-workflow.yaml`
**Purpose**: Full-featured workflow for complex migrations
**Use Case**: Large-scale migrations requiring analysis, backup, and validation
**Key Features**:
- 8-step comprehensive process
- Phased migration approach
- Risk assessment and rollback procedures
- Detailed success metrics and timeline estimates

### `ci-cd-workflow.yaml`
**Purpose**: Automated migration in CI/CD pipelines
**Use Case**: Integrating migration into automated build/deployment workflows
**Key Features**:
- Pipeline stages with automated steps
- Environment validation and dependency management
- Quality gates and security scanning
- Pull request automation and notifications

### `gradual-migration-workflow.yaml`
**Purpose**: Incremental migration of large codebases
**Use Case**: Migrating large projects over multiple iterations
**Key Features**:
- 4-phase approach with batch processing
- Progress monitoring and dashboards
- Risk mitigation strategies
- Resource planning and communication plans

### `legacy-code-workflow.yaml`
**Purpose**: Migration of older unittest code with deprecated patterns
**Use Case**: Converting legacy Python 2.7 code and old unittest patterns
**Key Features**:
- Legacy pattern detection and handling
- Compatibility layer creation
- Incremental conversion phases
- Special handling for deprecated features

## Workflow Structure

All workflow templates follow a consistent YAML structure:

```yaml
name: "Workflow Name"
description: "Brief description of the workflow"
version: "1.0.0"

# Prerequisites (optional)
prerequisites:
  - "Required condition 1"
  - "Required condition 2"

# Workflow Steps
steps:
  - name: "step_name"
    description: "What this step does"
    type: "step_type"
    config:
      setting1: value1
      setting2: value2

# Success Criteria
success_criteria:
  - "Measurable success indicator 1"
  - "Measurable success indicator 2"

# Troubleshooting (optional)
troubleshooting:
  - issue: "Common problem description"
    solution: "How to resolve it"
```

## Step Types

Workflows use standardized step types:

- `setup`: Environment preparation and validation
- `analysis`: Code analysis and assessment
- `backup`: Creating backups and recovery points
- `migration`: Code conversion and transformation
- `validation`: Testing and verification
- `reporting`: Report generation and communication
- `rollback`: Recovery procedures

## Using Workflows

### Manual Execution

1. Review the workflow prerequisites
2. Follow steps in order
3. Validate success criteria after each step
4. Use troubleshooting guide for issues

### Automated Execution

Workflows can be integrated into CI/CD systems:

```yaml
# GitHub Actions example
- name: Run Migration Workflow
  uses: your-org/migration-action@v1
  with:
    workflow: examples/workflow-templates/ci-cd-workflow.yaml
    config: examples/config-templates/ci-cd-integration.yaml
```

### Customization

1. Copy a workflow template
2. Modify steps and configuration for your needs
3. Add project-specific prerequisites or success criteria
4. Integrate with your existing processes

## Configuration Integration

Workflows reference configuration templates:

- `basic-migration.yaml`: Simple migrations
- `comprehensive-migration.yaml`: Complex migrations
- `ci-cd-integration.yaml`: Automated pipelines
- `batch-processing.yaml`: Multiple file processing
- `advanced-analysis.yaml`: Analysis-focused workflows

## Best Practices

1. **Start Small**: Begin with simple workflows for pilot migrations
2. **Scale Gradually**: Move to comprehensive workflows as you gain experience
3. **Automate When Possible**: Use CI/CD workflows for consistent, repeatable migrations
4. **Monitor Progress**: Track metrics and adjust approaches based on results
5. **Document Lessons**: Update workflows based on experience and challenges encountered

## Success Metrics

Track these metrics across migrations:

- **Completion Rate**: Percentage of planned migrations completed
- **Quality Score**: Test pass rates and code coverage maintenance
- **Time Efficiency**: Average time per file/function migrated
- **Error Rate**: Issues encountered and resolution time
- **User Satisfaction**: Stakeholder feedback on migration process

## Integration Points

Workflows integrate with:

- **Version Control**: Branching strategies and pull requests
- **CI/CD Systems**: Automated testing and deployment
- **Code Quality Tools**: Linting, security scanning, coverage analysis
- **Project Management**: Issue tracking and progress reporting
- **Communication Tools**: Notifications and status updates

## Troubleshooting Common Issues

### Workflow Execution Issues

**Problem**: Prerequisites not met
**Solution**: Review and complete all prerequisites before starting

**Problem**: Step failures
**Solution**: Check troubleshooting sections and logs for specific guidance

**Problem**: Configuration conflicts
**Solution**: Validate configuration against schema and test in isolation

### Migration Quality Issues

**Problem**: Test failures after migration
**Solution**: Review migration patterns and manually adjust complex cases

**Problem**: Performance regression
**Solution**: Profile code and optimize pytest patterns

**Problem**: Code quality degradation
**Solution**: Apply code quality improvements in optimization phase

## Contributing

To add new workflow templates:

1. Follow the established YAML structure
2. Include comprehensive success criteria
3. Add troubleshooting guidance
4. Test the workflow end-to-end
5. Document any special requirements