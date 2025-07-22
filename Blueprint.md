# Blueprint.md

## Introduction

This blueprint outlines the architecture for an automated Portfolio Health Report system designed for Directors of Engineering preparing for Quarterly Business Reviews. The system analyzes project communications from email text files to identify risks, inconsistencies, and unresolved issues, producing a concise report that directs executive attention to critical areas. 

The architecture prioritizes complete data isolation through offline processing, ensuring sensitive customer information never leaves the controlled environment. All components run on local or on-premises infrastructure, with an alternative option for isolated Azure deployments where data privacy is guaranteed through dedicated instances.

## 1. Data Ingestion & Initial Processing

The system ingests raw email text files from multiple project folders, processing multi-threaded conversations through a scalable pipeline. The ingestion process begins with parallel file scanning across project directories, followed by sophisticated parsing that extracts structured elements: timestamps, senders, recipients, subjects, thread relationships, and body content. 

For scalability on large datasets, the architecture employs distributed processing with data partitioning across multiple workers. This enables horizontal scaling on local clusters, handling terabytes of email data through batch processing and incremental updates. The pipeline includes:

- **Parsing & Extraction**: Multi-format email parsing handling quoted replies, forwards, and thread reconstruction
- **Cleaning & Normalization**: Removal of signatures, disclaimers, redundant quotes, and formatting noise
- **Chunking Strategy**: Intelligent segmentation by thread, conversation context, and temporal boundaries
- **Embedding Generation**: Local transformer models create semantic vector representations
- **Vector Database Indexing**: High-performance storage and retrieval of embeddings

### Vector Database Architecture

After comprehensive analysis of vector database options for offline deployment, **FAISS (Facebook AI Similarity Search)** emerges as the optimal choice, with **Chroma** as a viable alternative for specific use cases.

**FAISS Selection Rationale:**
- **Performance**: Sub-millisecond query times on billions of vectors through optimized C++ implementation
- **Scalability**: Multiple index types (Flat, IVF, HNSW, PQ) allowing accuracy/speed trade-offs
- **Offline Capability**: Zero external dependencies, runs entirely on local infrastructure
- **GPU Acceleration**: Native CUDA support for 10-100x speedup on similarity searches
- **Memory Efficiency**: Product quantization reduces memory footprint by 8-32x

**Implementation Considerations:**
- **Index Selection**: IVF-PQ for massive scale (billions of vectors), HNSW for moderate scale with higher accuracy
- **Sharding Strategy**: Distributed indices across nodes with consistent hashing for load balancing
- **Persistence**: Memory-mapped files for crash recovery and fast startup
- **Updates**: Batch index rebuilds scheduled during low-activity periods

**Alternative - Chroma:**
- Better for rapid prototyping with built-in metadata filtering
- Simpler Python integration but lower performance at scale
- Suitable for deployments under 100M vectors

**Security Integration:**
- All vector operations occur in-memory or on encrypted local storage
- No network calls or external APIs
- Access control through OS-level permissions and process isolation

```
Email Files → Parallel Ingestion → Parse & Clean → Chunk by Context → Generate Embeddings → FAISS Index
     ↓                                                                                              ↓
Project Metadata ←────────────────────────────────────────────────────→ Query Interface
```

## 2. The Analytical Engine (Multi-Step AI Logic)

The analytical engine implements sophisticated detection logic for two critical attention flags that demand immediate Director focus:

### Attention Flag 1: Unresolved High-Priority Action Items
**Definition**: Tasks, decisions, or questions that remain open beyond acceptable thresholds (configurable, default 7 days), particularly those with urgency indicators or involving key stakeholders.

**Detection Criteria**:
- Temporal analysis: Items without resolution within threshold period
- Priority signals: Keywords ("urgent", "critical", "blocker"), stakeholder involvement, escalation patterns
- Thread analysis: Absence of closure signals in subsequent messages

### Attention Flag 2: Emerging Risks/Blockers
**Definition**: Potential obstacles or threats mentioned without documented mitigation plans, including technical challenges, resource constraints, or dependency issues.

**Detection Criteria**:
- Risk language patterns: "concern", "blocked", "delayed", "shortage", "issue"
- Mitigation gap analysis: Absence of resolution discussion in thread context
- Impact assessment: Severity based on project timeline and stakeholder mentions

### Multi-Step AI Process

1. **Semantic Retrieval**: Query vector database for contextually relevant segments using embedding similarity
2. **Context Aggregation**: Cluster related communications across threads and time windows
3. **Entity Extraction**: Identify actions, risks, owners, and temporal markers using structured output
4. **Resolution Verification**: Cross-reference across communication timeline for closure signals
5. **Priority Scoring**: Rank by severity, age, stakeholder impact, and project criticality
6. **Evidence Compilation**: Link findings to source emails with confidence scores

### Hallucination Mitigation Strategies

- **Grounded Generation**: All outputs cite specific email segments from vector retrieval
- **Multi-Pass Validation**: Independent analysis runs with consistency checking
- **Confidence Thresholds**: Flags below 80% confidence marked for human review
- **Rule-Based Verification**: Heuristic overlays for critical patterns
- **Ensemble Approach**: Multiple model configurations vote on final classifications

### Security Integration

- All AI inference occurs offline on isolated hardware
- Data remains within air-gapped environment throughout processing
- PII anonymization during analysis phases
- Encrypted intermediate storage between pipeline steps
- Audit logging of all analytical decisions

## 3. Cost & Robustness Considerations

### Robustness Design

**Ambiguity Handling**:
- Semantic clarity scoring with fallback to conservative interpretation
- Multi-source corroboration requirements for high-impact flags
- Human-in-the-loop escalation for edge cases

**Error Recovery**:
- Checkpoint-based processing with automatic resume
- Graceful degradation when confidence is low
- Alternative analysis paths for failed components

**Data Quality Management**:
- Input validation and format detection
- Handling of corrupted or incomplete email threads
- Statistical outlier detection for anomalous patterns

### Cost Management Strategy

**Hardware Optimization**:
- Dynamic resource allocation based on workload
- Batch processing during off-peak hours
- Model quantization (INT8/INT4) reducing compute by 75% with minimal accuracy loss

**Caching Architecture**:
- Embedding cache for frequently accessed content
- Result memoization for common query patterns
- Incremental processing for new data only

**Resource Monitoring**:
- Real-time tracking of GPU/CPU utilization
- Automatic scaling within hardware limits
- Cost projection based on data growth trends

## 4. Monitoring & Trust

### Key Performance Metrics

**Accuracy Metrics**:
- Precision/Recall for each attention flag category
- False positive rate with weekly targets
- Human validation sampling at 5% of outputs

**Operational Metrics**:
- End-to-end latency (target: <5 minutes for daily report)
- System uptime (target: 99.9%)
- Processing throughput (emails/second)

**Trust Indicators**:
- Confidence score distribution
- Drift detection from baseline performance
- Audit trail completeness

### Monitoring Infrastructure

- Local Prometheus/Grafana stack for metrics visualization
- Automated alerting for threshold breaches
- Weekly performance reports with trend analysis
- Quarterly model performance reviews

### Continuous Improvement

- Feedback loops from Director reviews
- Fine-tuning on organization-specific patterns
- A/B testing of detection algorithms
- Regular security audits

## 5. Architectural Risk & Mitigation

### Primary Risk: Model Drift and Context Evolution

The most significant architectural risk is the degradation of detection accuracy over time as organizational communication patterns, terminology, and priorities evolve beyond the model's training distribution.

### Mitigation Strategy

1. **Continuous Learning Pipeline**:
   - Secure, isolated fine-tuning environment
   - Quarterly model updates with new communication patterns
   - Domain-specific vocabulary expansion

2. **Hybrid Intelligence**:
   - Rule-based overlays for organization-specific patterns
   - Human expert review integration
   - Configurable detection thresholds

3. **Monitoring and Early Warning**:
   - Statistical monitoring of language pattern changes
   - Performance degradation alerts
   - Automated retraining triggers

4. **Architectural Flexibility**:
   - Modular design allowing model swapping
   - Version control for all components
   - Rollback capabilities for all changes

## AI Models Used

### Primary Model: Llama 3.1 70B
The core analytical engine utilizes **Llama 3.1 70B** running entirely offline through local deployment frameworks (Ollama, llama.cpp). This model was selected after extensive evaluation for its:

- **Superior reasoning capabilities** for multi-step analysis and complex email thread understanding
- **Low hallucination rates** critical for accurate risk detection
- **Efficient quantization support** (GGUF format) enabling deployment on standard enterprise GPUs
- **Complete offline operation** ensuring zero data exposure to external networks
- **Open-source nature** allowing customization without licensing constraints

### Embedding Model: BGE-large-en-v1.5
For vector database population, **BGE-large-en-v1.5** provides:
- State-of-the-art semantic understanding for email content
- Optimized for retrieval tasks with high recall
- Compact 1024-dimensional embeddings balancing quality and storage
- Fully offline operation with excellent hardware efficiency

### Alternative: Azure OpenAI Service (Isolated Deployment)

For organizations requiring cloud scalability while maintaining data isolation, Azure OpenAI Service offers:

**Privacy Guarantees**:
- Customer data remains within dedicated Azure subscription
- No data used for model training or improvement
- No sharing with third parties including Microsoft or OpenAI
- Compliance with data residency requirements

**Technical Implementation**:
- Private endpoints within customer VNet
- Network isolation through Azure Private Link
- Customer-managed encryption keys
- Configurable data retention (immediate deletion available)
- Full audit logging within customer's Azure tenant