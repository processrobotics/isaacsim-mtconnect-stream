# MTConnect Stream Extension

An Isaac Sim extension for streaming MTConnect data from an MTConnect Agent.

## Requirements

Install the MTConnect REST Python library:

```bash
pip install git+https://github.com/processrobotics/mtconnect-rest-python.git
```

## Loading Extension

To enable this extension, run Isaac Sim with the flags:
```
--ext-folder {path_to_ext_folder} --enable isaacsim.mtconnect.stream
```

Or enable through the Extension Manager by providing its local path and searching for it in "Third Party Extensions".

## Usage

1. Open the extension from the menu bar: **MTConnect Stream** > **MTConnect Stream**
2. Enter the MTConnect Agent address (e.g., `http://localhost:5000`)
3. Click **START STREAM** to begin streaming data
4. Click **STOP STREAM** to stop streaming

## How It Works

1. **Connect**: Fetches `/current` response from the agent to get initial state
2. **Cache**: Stores data in a dict along with header info (instance ID, sequence numbers)
3. **Stream**: Polls `/sample?from={lastSequence}` to get updates
4. **Merge**: Incoming data is merged with the cached data

## Files

- `extension.py` - Extension boilerplate for Isaac Sim toolbar integration
- `ui_builder.py` - UI with agent address input and start/stop buttons
- `mtconnect_client.py` - MTConnect streaming client using mtconnect-rest-python
- `global_variables.py` - Extension title and default settings