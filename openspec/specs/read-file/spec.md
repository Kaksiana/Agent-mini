# read-file Specification

## Purpose
定义 read_file 契约：仅文本 codec、有界读取、file_not_found/file_read_error 区分与结构化错误。

## Requirements

### Requirement: 文本 codec 与编码错误

read_file MUST 只接受文本 codec；空编码或 `base64`/`hex` 等非文本 codec MUST invalid_encoding；decode 阶段 LookupError MUST invalid_encoding。

#### Scenario: 非文本 codec

- **WHEN** encoding=base64
- **THEN** invalid_encoding

#### Scenario: 空编码

- **WHEN** encoding=""
- **THEN** invalid_encoding
