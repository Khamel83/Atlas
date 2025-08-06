---
description: Execute All ~300 Unified Atlas-Podemos Tasks Automatically
globs:
alwaysApply: false
version: 1.0
encoding: UTF-8
---

# Execute Unified Atlas-Podemos System

<ai_meta>
  <rules>Execute all ~300 unified tasks sequentially with full Atlas-Podemos integration</rules>
  <format>UTF-8, LF, 2-space indent, automated execution</format>
</ai_meta>

## Overview

Execute all ~300 unified Atlas-Podemos tasks automatically from current state to fully production-ready integrated cognitive amplification platform. This includes completing the integration work AND the full production-ready system with advanced podcast processing.

## Task Sources

### Integration Tasks (Major Tasks 1-15 from Atlas-Podemos spec)
- **Location**: `@.agent-os/specs/2025-08-05-atlas-podemos-integration/tasks.md`
- **Status**: Major Task 1 COMPLETED ✅
- **Remaining**: Major Tasks 2-15 (Database Integration → Advanced Features)

### Production Tasks (Major Tasks 3-26 from original Atlas spec)  
- **Location**: `@.agent-os/specs/2025-08-01-atlas-production-ready-system/tasks.md`
- **Status**: Major Tasks 0-2 COMPLETED ✅
- **Remaining**: Major Tasks 3-26 (Configuration → Final Validation)

### Master Task List
- **Location**: `MASTER_TASKS.md`
- **Contains**: Consolidated view of all ~300 tasks with current priority order

## Execution Strategy

### Phase 1A: Complete Integration Foundation (Weeks 1-3)
**Current Status**: Major Task 1 COMPLETED ✅
**Next**: Execute Major Tasks 2-3 from integration spec

1. **Major Task 2**: Database Integration (7 subtasks)
2. **Major Task 3**: Core Module Integration (7 subtasks)

### Phase 1B: Production System Phase 1 (Week 4)
Execute remaining Atlas production Phase 1 with integrated architecture:

1. **Major Task 3**: Configuration Management Enhancement (7 subtasks)
2. **Major Task 4**: Error Handling & Logging Enhancement (7 subtasks)  
3. **Major Task 5**: Basic Security Implementation (7 subtasks)

### Phase 2: Unified System Core Features (Weeks 5-8)
Execute both integration and production core features:

**Integration Tasks**:
- Major Task 4: Processing Pipeline Integration
- Major Task 5: Cognitive Analysis Integration
- Major Task 6: Storage System Integration

**Production Tasks**:
- Major Task 6: Performance Optimization Infrastructure
- Major Task 7: Full-Text Search Implementation
- Major Task 8: Enhanced Cognitive Features
- Major Task 9: Advanced AI Integration
- Major Task 10: Content Analytics and Insights

### Phase 3: Interface & API Development (Weeks 9-12)
**Integration Tasks**:
- Major Task 7: Web Dashboard Integration
- Major Task 8: API Integration
- Major Task 9: Configuration Integration

**Production Tasks**:
- Major Task 11: Core API Framework
- Major Task 12: Authentication & Security API
- Major Task 13: Content Management API
- Major Task 14: Search & Query API
- Major Task 15: Cognitive Amplification API

### Phase 4: Production Hardening (Weeks 13-16)
**Integration Tasks**:
- Major Task 10: Performance Optimization
- Major Task 11: Advanced Features
- Major Task 12: Testing & Validation

**Production Tasks**:
- Major Task 16: Monitoring & Observability
- Major Task 17: Backup & Recovery Systems
- Major Task 18: Automated Maintenance
- Major Task 19: Deployment Automation
- Major Task 20: Security Hardening

### Phase 5: Documentation & Completion (Weeks 17-20)
**Integration Tasks**:
- Major Task 13: Documentation Integration
- Major Task 14: Deployment & Migration Tools
- Major Task 15: Final Integration Validation

**Production Tasks**:
- Major Task 21: Comprehensive Documentation
- Major Task 22: GitHub Automation & Workflow
- Major Task 23: Development Workflow Optimization
- Major Task 24: System Integration Testing
- Major Task 25: Performance Validation & Optimization
- Major Task 26: Production Readiness Validation

## Execution Flow

<execution_flow>

<step number="1" name="initialization">

### Step 1: System Initialization

<prerequisite_validation>
  <required_files>
    - MASTER_TASKS.md
    - @.agent-os/specs/2025-08-05-atlas-podemos-integration/tasks.md
    - @.agent-os/specs/2025-08-01-atlas-production-ready-system/tasks.md
    - helpers/config_unified.py
    - helpers/podcast_processor_unified.py
    - run.py (unified entry point)
  </required_files>
  <integration_validation>
    - Atlas-Podemos foundation integration completed
    - Unified configuration system operational  
    - Integrated entry point functional
    - All Atlas cognitive modules preserved
  </integration_validation>
</prerequisite_validation>

<instructions>
  ACTION: Validate unified system prerequisites
  LOAD: Complete task database from both specifications
  BUILD: Dependency resolution for integrated system
  INITIALIZE: Progress tracking for ~300 tasks
</instructions>

</step>

<step number="2" name="execution_planning">

### Step 2: Unified Execution Planning

<critical_path_identification>
  - Integration Task 2.7: Database schema integration (blocks all data operations)
  - Integration Task 4.8: Processing pipeline integration (blocks content flow)
  - Production Task 6.2: Redis installation (blocks performance features)
  - Integration Task 7.8: Web dashboard integration (blocks user interface)
  - Production Task 19.8: Deployment automation (blocks production readiness)
</critical_path_identification>

<parallel_opportunities>
  - Integration Phase 2: Tasks 4, 5, 6 can run simultaneously
  - Production Phase 2: Tasks 6, 7, 8, 9, 10 can be parallel where not dependent
  - Phase 3: API and interface tasks can be largely parallel
  - Phase 4: Production hardening tasks can be parallel
</parallel_opportunities>

<instructions>
  ACTION: Analyze dependencies across both specifications
  IDENTIFY: Critical path through integrated system
  PLAN: Optimal execution order maximizing parallelization
  PREPARE: Resource strategies for both Atlas and Podemos components
</instructions>

</step>

<step number="3" name="automated_execution">

### Step 3: Unified Automated Execution

<execution_loop>
  WHILE unified_tasks_remaining():

    # Get ready tasks from both specifications
    ready_tasks = unified_dependency_resolver.get_ready_tasks()

    FOR EACH task_id in ready_tasks:

      # Load complete context (Atlas + Podemos + Integration)
      context = unified_context_loader.load_task_context(task_id)

      # Generate execution prompt with full integration context
      prompt = unified_context_loader.generate_unified_task_prompt(task_id, context)

      # Execute task using appropriate system (Atlas/Podemos/Unified)
      result = execute_unified_task(task_id, prompt)

      # Validate quality gates for integrated system
      quality_result = unified_quality_validator.validate_task_completion(task_id)

      IF quality_result.all_passed():
        # Commit changes with integration context
        git_automation.commit_unified_task_completion(task_id, result)
        
        # Update both task tracking systems
        unified_task_database.mark_task_completed(task_id, result)
        master_tasks_tracker.update_completion_status(task_id)

      ELSE:
        # Attempt quality recovery with unified system context
        recovery_success = unified_quality_recovery.attempt_fixes(task_id, quality_result)

    # Save unified execution checkpoint
    unified_progress_tracker.save_checkpoint()

    # Generate comprehensive progress report
    progress_report = unified_progress_tracker.generate_unified_progress_report()

</execution_loop>

<instructions>
  ACTION: Execute main unified automation loop
  MANAGE: Dependencies across both Atlas and Podemos components
  HANDLE: Integration-specific failures and quality gates
  TRACK: Progress across all ~300 tasks with unified reporting
</instructions>

</step>

</execution_flow>

## Success Criteria

<unified_success_criteria>
  <functional_requirements>
    - Single deployment supports complete RSS → insights pipeline
    - Atlas cognitive features work with Podemos-processed content
    - Unified web dashboard shows both processing and insights
    - All original Atlas functionality preserved and enhanced
    - Advanced podcast processing with ad removal operational
  </functional_requirements>

  <performance_requirements>
    - Processing time ≤ 150% of standalone Podemos
    - Cognitive analysis time ≤ 110% of standalone Atlas
    - Memory usage ≤ 130% of individual systems
    - Test coverage ≥ 90% for unified functionality
  </performance_requirements>

  <integration_requirements>
    - Zero data loss during integration
    - Backward compatibility for existing configurations
    - Graceful fallback when Podemos components unavailable
    - Complete unified documentation and setup guides
  </integration_requirements>
</unified_success_criteria>

## Quality Gates

<unified_quality_gates>
  <integration_gates>
    - Atlas cognitive modules preserved and functional
    - Podemos processing components properly integrated
    - Unified configuration system operational
    - Data flows correctly between systems
  </integration_gates>
  
  <production_gates>
    - All original Atlas production requirements met
    - Enhanced with Podemos advanced capabilities
    - Production deployment procedures validated
    - Complete system monitoring and alerting
  </production_gates>
</unified_quality_gates>

This unified execution system creates a best-in-class cognitive amplification platform that combines the best of both Atlas and Podemos while maintaining all original functionality and adding advanced podcast processing capabilities.