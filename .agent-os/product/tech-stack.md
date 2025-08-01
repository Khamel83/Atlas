# Atlas Technical Stack

## Core Technologies

- **Primary Language**: Python
- **Web Framework**: FastAPI (implied by existing codebase)
- **LLM Access**: OpenRouter API (user preference)

## Deployment & Infrastructure

- **Preferred Deployment Target**: Raspberry Pi (for self-hosting and low-power operation)
- **Supplemental Compute**: Mac Mini M4 with 16GB RAM (for intensive tasks like transcription, benefiting from local processing power)
- **Storage**: Extensive use of spinning disks for large data volumes (user preference for personal data collection).

## Philosophy

- **Open Source**: The project is intended to be entirely open source.
- **Self-Hosted**: Emphasis on self-hosting to ensure data ownership and avoid subscription models.

## Future Considerations

- The current codebase suggests a sophisticated modular design with a 6-layer content fallback system, indicating a complex data processing pipeline.
- The user's preference for a Raspberry Pi suggests a focus on efficiency and local control, while the Mac Mini M4 indicates a pragmatic approach to offloading computationally intensive tasks.