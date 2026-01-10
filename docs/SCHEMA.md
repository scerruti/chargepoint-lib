# Data Schema

JSON schemas for all data structures in CPH50 Control.

## Session Cache Schema

File: `data/session_cache/YYYY-MM.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "title": "Session Cache (Monthly)",
  "description": "Minimal session data cached for history display. Array of sessions organized by month.",
  "items": {
    "type": "object",
    "required": ["session_id", "session_start_time", "session_end_time", "energy_kwh"],
    "properties": {
      "session_id": {
        "type": ["string", "integer"],
        "description": "Unique session identifier from ChargePoint API"
      },
      "session_start_time": {
        "type": "string",
        "format": "date-time",
        "description": "UTC timestamp when session started"
      },
      "session_end_time": {
        "type": ["string", "null"],
        "format": "date-time",
        "description": "UTC timestamp when session ended"
      },
      "energy_kwh": {
        "type": ["number", "null"],
        "description": "Total energy delivered in kilowatt-hours"
      },
      
    }
  }
}
```

---

## Session Data Schema

File: `data/sessions/YYYY/MM/DD/{session_id}.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Charging Session Data",
  "description": "Complete record of a charging session with 5-minute sample collection",
  "required": ["session_id", "collection_start", "collection_end", "duration_seconds", "samples"],
  "properties": {
    "session_id": {
      "type": ["string", "integer"],
      "description": "Unique session identifier from ChargePoint API"
    },
    "collection_start": {
      "type": "string",
      "format": "date-time",
      "description": "UTC timestamp when data collection began"
    },
    "collection_end": {
      "type": "string",
      "format": "date-time",
      "description": "UTC timestamp when data collection ended"
    },
    "duration_seconds": {
      "type": "number",
      "description": "Total collection duration in seconds"
    },
    "sample_count": {
      "type": "integer",
      "description": "Total number of samples collected"
    },
    "valid_sample_count": {
      "type": "integer",
      "description": "Number of samples with valid power/energy data"
    },
    "interval_seconds": {
      "type": "integer",
      "description": "Interval between samples in seconds"
    },
    "vehicle_id": {
      "type": "string",
      "enum": ["serenity_equinox_2024", "volvo_xc40_2021", "unknown"],
      "description": "Key to vehicle_config.json"
    },
    "vehicle_confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "ML classifier confidence score (0-1)"
    },
    "labeled_by": {
      "type": ["string", "null"],
      "enum": ["classifier", "manual", null],
      "description": "How vehicle was identified"
    },
    "labeled_at": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "When vehicle was identified"
    },
    "samples": {
      "type": "array",
      "minItems": 1,
      "items": {
        "$ref": "#/definitions/Sample"
      },
      "description": "Array of power/energy samples"
    }
  },
  "definitions": {
    "Sample": {
      "type": "object",
      "required": ["sample_number", "timestamp", "power_kw", "energy_kwh"],
      "properties": {
        "sample_number": {
          "type": "integer",
          "description": "Sequential sample number (1-indexed)"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "UTC timestamp of sample"
        },
        "timestamp_pt": {
          "type": "string",
          "description": "Human-readable PT timezone timestamp"
        },
        "session_id": {
          "type": ["string", "integer"],
          "description": "Session ID (for reference)"
        },
        "power_kw": {
          "type": ["number", "null"],
          "description": "Instantaneous power draw in kilowatts"
        },
        "energy_kwh": {
          "type": ["number", "null"],
          "description": "Cumulative energy delivered in kilowatt-hours"
        },
        "duration_minutes": {
          "type": ["number", "null"],
          "description": "Session duration in minutes (from API)"
        },
        "status": {
          "type": ["string", "null"],
          "description": "Session status at time of sample"
        }
      }
    }
  }
}
```

---

## Vehicle Configuration Schema

File: `data/vehicle_config.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Vehicle Configuration",
  "required": ["vehicles"],
  "properties": {
    "vehicles": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/definitions/Vehicle"
      },
      "description": "Dictionary of vehicles keyed by vehicle_id"
    },
    "last_updated": {
      "type": "string",
      "format": "date-time",
      "description": "When this config was last updated"
    }
  },
  "definitions": {
    "Vehicle": {
      "type": "object",
      "required": ["nickname", "make", "model", "year"],
      "properties": {
        "nickname": {
          "type": "string",
          "description": "Display name (e.g., 'Serenity')"
        },
        "year": {
          "type": "integer",
          "minimum": 2000,
          "description": "Model year"
        },
        "make": {
          "type": "string",
          "description": "Manufacturer (e.g., 'Chevrolet')"
        },
        "model": {
          "type": "string",
          "description": "Model name (e.g., 'Equinox EV')"
        },
        "trim": {
          "type": "string",
          "description": "Trim level (e.g., '2LT')"
        },
        "battery_capacity_kwh": {
          "type": "number",
          "minimum": 0,
          "description": "Total usable battery capacity in kWh"
        },
        "max_charge_rate_kw": {
          "type": "number",
          "minimum": 0,
          "description": "Maximum charging power in kW"
        },
        "paint_color": {
          "type": "string",
          "description": "Actual paint color name (e.g., 'Bursting Blue')"
        },
        "paint_color_hex": {
          "type": "string",
          "pattern": "^#[0-9a-fA-F]{6}$",
          "description": "Paint color as hex code (e.g., '#2C5F8D')"
        },
        "display_color": {
          "type": "string",
          "description": "Simple color for UI display/disambiguation (e.g., 'Blue')"
        },
        "efficiency_mi_per_kwh": {
          "type": "number",
          "minimum": 0,
          "description": "Estimated efficiency in miles per kWh"
        },
        "characteristics": {
          "type": "string",
          "description": "Human-readable notes on charging behavior"
        }
      }
    }
  }
}
```

---

## Last Session Snapshot Schema

File: `data/last_session.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Last Session Snapshot",
  "description": "Dashboard snapshot of current/recent charging status",
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "UTC timestamp of last update"
    },
    "detected_at": {
      "type": "string",
      "description": "Human-readable PT timezone detection time"
    },
    "power_kw": {
      "type": ["number", "null"],
      "minimum": 0,
      "description": "Current power draw in kW (null if not charging)"
    },
    "energy_kwh": {
      "type": ["number", "null"],
      "minimum": 0,
      "description": "Total energy delivered in current session"
    },
    "duration_minutes": {
      "type": ["integer", "null"],
      "minimum": 0,
      "description": "Session duration in minutes"
    },
    "vehicle_id": {
      "type": ["string", "null"],
      "enum": ["serenity_equinox_2024", "volvo_xc40_2021", "unknown", null],
      "description": "Identified vehicle (null if not detected)"
    },
    "vehicle_confidence": {
      "type": ["number", "null"],
      "minimum": 0,
      "maximum": 1,
      "description": "ML confidence in vehicle identification (0-1)"
    },
    "connected": {
      "type": "boolean",
      "description": "Charger physically connected"
    },
    "charging": {
      "type": "boolean",
      "description": "Active charging in progress"
    }
  },
  "required": ["timestamp", "connected", "charging"]
}
```

---

## Runs History Schema

File: `data/runs.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Automation Runs History",
  "description": "Record of test/deployment run attempts",
  "properties": {
    "runs": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Run"
      }
    }
  },
  "definitions": {
    "Run": {
      "type": "object",
      "required": ["run_id", "date", "result"],
      "properties": {
        "run_id": {
          "type": "string",
          "description": "Unique run identifier"
        },
        "date": {
          "type": "string",
          "format": "date",
          "description": "Date of run (YYYY-MM-DD)"
        },
        "time_utc": {
          "type": "string",
          "description": "UTC time (HH:MM:SS)"
        },
        "time_pt": {
          "type": "string",
          "description": "PT time (HH:MM:SS)"
        },
        "result": {
          "type": "string",
          "enum": ["success", "failure", "other"],
          "description": "Outcome of the run"
        },
        "reason": {
          "type": "string",
          "description": "Description (e.g., failure reason)"
        },
        "run_type": {
          "type": "string",
          "description": "Type of run (e.g., 'scheduled', 'manual')"
        }
      }
    }
  }
}
```

---

## Adding New Data Files

When adding a new data file or modifying existing schemas:

1. **Update this file** (`docs/SCHEMA.md`) with the JSON Schema
2. **Update DATA_DICTIONARY.md** with:
   - File path and purpose
   - Created/Updated by which component
   - Read by which components
   - Update frequency
   - Key fields description
3. **Commit both files** with the code changes
4. **Add validation** in writing components (optional but recommended)

---

**Schema Version**: 1.0  
**Last Updated**: 2026-01-10
