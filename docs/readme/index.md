# MQTT CLI Tool Documentation

## Overview

This is the documentation for the MQTT CLI tool, a command-line interface for MQTT operations.

## Installation

```bash
pip install rm-node
```

## Basic Usage

The basic command format is:

```bash
rm-node [OPTIONS] COMMAND [ARGS]...
```

### Common Examples

1. Connect to a node:
```bash
rm-node connection connect --node-id your-node-id
```

2. Send a device command:
```bash
rm-node device send-command --node-id your-node-id --role 1 --command 0
```

3. Monitor MQTT messages:
```bash
rm-node messaging monitor --topic "your/topic/#"
```

## Command Groups

- `connection`: Manage MQTT connections
- `messaging`: Handle MQTT pub/sub operations
- `device`: Device management commands
- `ota`: OTA update operations
- `node`: Node configuration and presence
- `user`: User-node mapping operations
- `tsdata`: Time series data operations
- `config`: Configuration management

## Quick Links

- [CLI Structure and Implementation](structure.md)
- [Getting Started](#getting-started)
- [Global Options](#global-options)

## Global Options

The CLI supports several global options that can be used with any command:

```bash
rm-node [OPTIONS] COMMAND [ARGS]...

Options:
  --config-dir DIRECTORY  Configuration directory path
  --debug                Enable debug mode with detailed logging
  --broker TEXT          MQTT broker endpoint to use
                        (default: mqtt://a1p72mufdu6064-ats.iot.us-east-1.amazonaws.com)
  -h, --help            Show this help message
```

## Getting Started

1. Installation
```bash
pip install rm-node
```

2. Basic Usage
```bash
# Connect to a node
rm-node connection connect --node-id your-node-id

# Send a command to a device
rm-node device send-command --node-id your-node-id --role 1 --command 0

# Monitor messages on a topic
rm-node messaging monitor --topic "your/topic/#"
```

For detailed documentation on each command group, please refer to their respective pages linked above. 