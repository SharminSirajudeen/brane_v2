# BRANE Neuron Configuration Library

## Overview

This directory contains production-ready Neuron configurations for BRANE's privacy-first AI agent platform. Each configuration is optimized for specific industries with appropriate privacy controls, compliance frameworks, and specialized tools.

## Available Neurons

### 1. Medical Assistant (`medical-assistant.yaml`)
**Industry**: Healthcare
**Privacy Tier**: 0 (Local Only)
**Compliance**: HIPAA, HITECH Act
**Model**: Ollama with medical-tuned models (local)

#### Key Features:
- **Complete Local Processing**: All PHI remains on-device, no cloud transmission
- **Medical Expertise**: Comprehensive medical knowledge with evidence-based recommendations
- **Clinical Decision Support**: Diagnostic reasoning, drug interactions, clinical calculators
- **PHI Protection**: Automatic redaction, session-based memory, audit logging
- **Safety Protocols**: Emergency detection, red flag alerts, contraindication warnings

#### Use Cases:
- Clinical decision support for healthcare providers
- Medical literature research and summarization
- Drug interaction and dosing verification
- Patient education material generation
- Clinical documentation assistance

#### Setup Requirements:
1. Install Ollama locally: `curl -fsSL https://ollama.ai/install.sh | sh`
2. Pull medical model: `ollama pull medllama2:13b`
3. Configure local storage encryption keys
4. Set up audit log retention (7 years per HIPAA)
5. Enable multi-factor authentication for access

### 2. Legal Research Assistant (`legal-researcher.yaml`)
**Industry**: Legal
**Privacy Tier**: 1 (Private Cloud)
**Compliance**: ABA Model Rules, GDPR, CCPA
**Model**: Claude 3 Opus (private deployment) with Azure OpenAI fallback

#### Key Features:
- **Privilege Protection**: Attorney-client and work product privilege detection
- **Legal Expertise**: Case law analysis, statutory interpretation, citation formatting
- **Research Tools**: Westlaw/Lexis integration, brief analysis, conflict checking
- **Jurisdiction Awareness**: Federal and state law variations, local rules
- **Ethical Compliance**: ABA Model Rules adherence, inadvertent disclosure prevention

#### Use Cases:
- Legal research and case law analysis
- Brief and motion drafting assistance
- Contract review and risk assessment
- Citation formatting and validation
- Discovery document analysis
- Regulatory compliance research

#### Setup Requirements:
1. Configure private Anthropic deployment with DPA
2. Set up Azure OpenAI with signed BAA as fallback
3. Install legal-bert embedding model
4. Configure matter-based memory segregation
5. Set up privilege detection and logging system
6. Implement conflict checking database connection

### 3. Financial Analyst (`financial-analyst.yaml`)
**Industry**: Finance
**Privacy Tier**: 1 or 2 (Configurable)
**Compliance**: SOC2 Type II, SEC, FINRA, PCI-DSS
**Model**: Azure OpenAI GPT-4 Turbo with Claude fallback

#### Key Features:
- **Market Analysis**: Real-time data integration, technical and fundamental analysis
- **Risk Management**: VaR calculations, stress testing, portfolio optimization
- **Regulatory Compliance**: SEC/FINRA rules, MNPI handling, audit trails
- **Quantitative Tools**: Option pricing, DCF models, statistical arbitrage
- **Data Integrity**: Source validation, corporate actions handling, backtesting

#### Use Cases:
- Investment research and analysis
- Portfolio risk assessment
- Regulatory reporting and compliance
- Market surveillance and anomaly detection
- Credit risk evaluation
- Trading strategy development

#### Setup Requirements:
1. Configure Azure OpenAI with SOC2-compliant deployment
2. Set up market data feeds (Bloomberg, Refinitiv, etc.)
3. Install FinBERT embedding model
4. Configure MNPI detection and isolation
5. Set up data residency controls
6. Implement high-availability failover
7. Configure compliance monitoring alerts

## Privacy Tiers Explained

### Tier 0: Local Only
- All processing happens on local infrastructure
- No data leaves the organization's control
- Required for HIPAA PHI, highly sensitive data
- Example: Medical Assistant

### Tier 1: Private Cloud
- Processing on private cloud with signed agreements (BAA/DPA)
- Data remains within organizational control
- Suitable for privileged information, MNPI
- Examples: Legal Research Assistant, Financial Analyst

### Tier 2: Public API
- Can use public cloud APIs with appropriate controls
- Suitable for non-sensitive, public information
- Includes data anonymization and encryption
- Example: Financial Analyst (public market data mode)

## Configuration Structure

Each YAML file follows this structure:

```yaml
metadata:           # Neuron identification and description
privacy_tier:       # 0, 1, or 2 based on data sensitivity
model:              # LLM provider and settings
prompts:            # System and user prompts
axon:               # RAG/vector database configuration
tools:              # MCP tools and integrations
memory:             # Conversation and context management
compliance:         # Industry-specific compliance settings
performance:        # Resource allocation and optimization
integrations:       # External system connections
```

## Customization Guide

### Adjusting for Your Organization

1. **Model Selection**:
   - Update `model.provider` and `model.model` based on your licenses
   - Adjust temperature and token limits for your use case
   - Configure fallback models for high availability

2. **Privacy Settings**:
   - Choose appropriate `privacy_tier` based on data sensitivity
   - Configure encryption keys in `axon.encryption`
   - Set data retention policies in `compliance.data_retention`

3. **Tool Configuration**:
   - Enable/disable tools based on available integrations
   - Update API endpoints and credentials
   - Configure tool-specific parameters

4. **Compliance Adjustments**:
   - Update `compliance.framework` for your jurisdiction
   - Adjust audit retention periods
   - Configure access control requirements

### Adding Custom Tools

To add new tools to a Neuron:

```yaml
tools:
  - id: "custom_tool_id"
    name: "Custom Tool Name"
    enabled: true
    config:
      endpoint: "https://api.example.com"
      api_key_env: "CUSTOM_API_KEY"
      features:
        - "feature_1"
        - "feature_2"
```

### Modifying System Prompts

System prompts can be customized for specific organizational needs:

```yaml
prompts:
  system: |
    [Your custom system prompt here]
    Include:
    - Role definition
    - Expertise areas
    - Behavioral guidelines
    - Safety protocols
    - Compliance requirements
```

## Deployment Instructions

### Local Deployment (Tier 0)

1. **Install Dependencies**:
   ```bash
   # Install Ollama for local models
   curl -fsSL https://ollama.ai/install.sh | sh

   # Pull required models
   ollama pull medllama2:13b
   ```

2. **Configure Environment**:
   ```bash
   # Set up environment variables
   export BRANE_CONFIG_PATH=/path/to/config
   export BRANE_STORAGE_PATH=/path/to/storage
   export BRANE_ENCRYPTION_KEY=$(openssl rand -base64 32)
   ```

3. **Initialize Storage**:
   ```bash
   # Create encrypted storage directories
   mkdir -p ./storage/axon/{medical,legal,finance}
   chmod 700 ./storage/axon/*
   ```

### Private Cloud Deployment (Tier 1)

1. **Cloud Provider Setup**:
   ```bash
   # Azure setup for GPT-4
   az cognitiveservices account create \
     --name finance-gpt4 \
     --resource-group brane-rg \
     --kind OpenAI \
     --sku S0 \
     --location eastus
   ```

2. **Configure Private Endpoints**:
   - Set up VPN or private link connections
   - Configure firewall rules for API access
   - Implement API key rotation

3. **Sign Legal Agreements**:
   - Business Associate Agreement (BAA) for healthcare
   - Data Processing Agreement (DPA) for GDPR
   - Custom legal services agreement for law firms

### Public API Deployment (Tier 2)

1. **API Configuration**:
   ```bash
   # Set API keys securely
   export OPENAI_API_KEY="sk-..."
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. **Rate Limiting**:
   - Configure rate limits to manage costs
   - Implement retry logic with exponential backoff
   - Set up usage monitoring and alerts

## Monitoring and Maintenance

### Health Checks

Each Neuron includes monitoring configuration:

```yaml
monitoring:
  health_check_interval_seconds: 60
  alert_on_errors: true
  metrics_collection: "local_only"
```

### Audit Logging

All Neurons maintain comprehensive audit logs:

- **Medical**: 7-year retention per HIPAA
- **Legal**: 10-year retention for legal records
- **Financial**: 7-year retention per SEC requirements

### Performance Optimization

1. **Memory Management**:
   - Adjust `performance.max_memory_gb` based on workload
   - Configure cache sizes for frequently accessed data

2. **GPU Acceleration**:
   - Enable `performance.gpu_enabled` for faster inference
   - Configure CUDA settings for Ollama

3. **Load Balancing**:
   - Implement multiple Neuron instances for high availability
   - Configure round-robin or least-connections routing

## Security Best Practices

1. **Access Control**:
   - Implement multi-factor authentication
   - Use role-based access control (RBAC)
   - Regular access reviews and deprovisioning

2. **Data Protection**:
   - Enable encryption at rest and in transit
   - Implement data loss prevention (DLP) policies
   - Regular security audits and penetration testing

3. **Incident Response**:
   - Maintain incident response procedures
   - Configure automated alerting for security events
   - Regular disaster recovery drills

## Troubleshooting

### Common Issues

1. **Model Loading Failures**:
   ```bash
   # Check Ollama status
   ollama list
   systemctl status ollama

   # Verify model availability
   ollama pull medllama2:13b
   ```

2. **API Connection Errors**:
   ```bash
   # Test API connectivity
   curl -X POST https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **Memory Issues**:
   ```bash
   # Check memory usage
   free -h

   # Adjust memory limits in config
   # performance.max_memory_gb: 8
   ```

### Support Resources

- **Documentation**: [Full BRANE documentation]
- **Community Forum**: [BRANE community support]
- **Enterprise Support**: Contact your account manager
- **Security Issues**: security@brane.ai

## Compliance Certifications

Each Neuron configuration includes compliance frameworks:

- **Healthcare**: HIPAA, HITECH, GDPR (for EU operations)
- **Legal**: ABA Model Rules, State Bar Requirements, GDPR, CCPA
- **Financial**: SOC2 Type II, SEC, FINRA, Basel III, PCI-DSS

## Version History

- **v1.0.0** (2025-01-01): Initial production configurations
  - Medical Assistant with HIPAA compliance
  - Legal Research Assistant with privilege protection
  - Financial Analyst with SOC2 compliance

## Contributing

To contribute new Neuron configurations:

1. Follow the existing YAML schema
2. Include comprehensive documentation
3. Ensure compliance requirements are met
4. Add appropriate test cases
5. Submit pull request with detailed description

## License

These configurations are provided as part of the BRANE platform. Usage is subject to BRANE's terms of service and licensing agreements.