JSON_SCHEMA_3 = """
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/boq.schema.json",
  "title": "Bill of Quantities (ВОР) file",
  "description": "Схема валидации файла ВОР (формат JSON, сохранённый BoQ_manager.save_file)",

  "type": "object",
  "required": ["metadata", "data"],
  "additionalProperties": true,

  "properties": {
    "data_scheme": {
      "description": "Версия схемы данных. save_file пишет 3; чтение поддерживает 1, 2, 3",
      "type": "integer",
      "enum": [1, 2, 3],
	  "default": 1
    },
    "metadata": { "$ref": "#/$defs/Metadata" },
    "data":     { "$ref": "#/$defs/Data" }
  },

  "$defs": {

    "Metadata": {
      "type": "object",
      "additionalProperties": true,
      "required": ["ObjectName"],
      "properties": {
        "ObjectName":       { "type": ["string", "null"] },
        "Num":              { "type": ["string", "null"] },
        "local_estimate":   { "type": ["string", "null"] },
        "Date":             { "type": "string" },
        "Signatures": {
          "type": "object",
          "additionalProperties": false,
          "required": ["Composer", "Composer_Position"],
          "properties": {
            "Composer":          { "type": "string" },
            "Composer_Position": { "type": "string" }
          }
        },
        "Verifier": {
          "description": "Произвольный словарь или null",
          "type": ["object", "null"]
        },
        "Status": {
          "type": "integer",
          "enum": [0, 1, 2]
        },
        "log_list": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "Date":  { "type": "string" },
              "Event": { "type": "string" }
            }
          }
        },
        "note": { "type": "string" }
      }
    },

    "Data": {
      "type": "object",
      "additionalProperties": false,
      "required": ["sections", "archive"],
      "properties": {
        "sections": {
          "type": "array",
          "items": { "$ref": "#/$defs/Section" }
        },
        "archive": {
          "type": "array",
          "items": { "$ref": "#/$defs/Section" }
        }
      }
    },

    "Section": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "works"],
      "properties": {
        "format_address_cache": { "type": ["string", "null"] },
        "name":                 { "type": "string" },
        "local_comment":        { "type": ["string", "null"] },
        "works": {
          "type": "array",
          "items": { "$ref": "#/$defs/Work" }
        }
      }
    },

    "Link": {
      "type": "object",
      "additionalProperties": false,
      "required": ["book_num", "tag", "user_pages"],
      "properties": {
        "book_num":   { "type": "string" },
        "tag":        { "type": ["integer", "null"] },
        "user_pages": { "type": ["string", "null"] }
      }
    },

    "StyleManager": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "col_2": { "$ref": "#/$defs/ColumnStyle" },
        "col_5": { "$ref": "#/$defs/ColumnStyle" },
        "col_6": { "$ref": "#/$defs/ColumnStyle" },
        "col_7": { "$ref": "#/$defs/ColumnStyle" },
        "col_9": { "$ref": "#/$defs/ColumnStyle" }
      }
    },

    "ColumnStyle": {
      "type": ["object", "null"],
      "additionalProperties": false,
      "properties": {
        "background_color": {
          "type": "string",
          "pattern": "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$"
        },
        "text_color": {
          "type": "string",
          "pattern": "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$"
        }
      }
    },

    "PositionLineFields": {
      "description": "Общие поля PositionLine (Work и Resource)",
      "type": "object",
      "properties": {
        "format_address_cache":   { "type": ["string", "null"] },
        "num_cache":              { "type": ["integer", "string", "null"] },
        "raw_name":               { "type": "string" },
        "name_hash":              { "type": ["string", "null"] },
        "name_cache":             { "type": ["string", "null"] },
        "raw_unit":               { "type": "string" },
        "raw_quantity_formula":   { "type": "string" },
        "quantity_formula_cache": { "type": ["string", "null"] },
        "quantity_cache":         { "type": ["string", "null"] },
        "raw_comment":            { "type": "string" },
        "comment_hash":           { "type": ["string", "null"] },
        "comment_cache":          { "type": ["string", "null"] },
        "local_comment":          { "type": ["string", "null"] },
        "type": {
          "type": "string",
          "enum": [
            "работа", "материал", "перевозка",
            "оборудование", "машина", "прочее"
          ]
        },
        "custom_round":      { "type": ["integer", "null"] },
        "custom_round_mode": {
          "type": ["integer", "null"],
          "enum": [null, 1, 2]
        },
        "style_manager":      { "$ref": "#/$defs/StyleManager" },
        "status_correct":     { "type": "boolean" },
        "status_calculated":  { "type": "boolean" },
        "links": {
          "type": "array",
          "items": { "$ref": "#/$defs/Link" }
        },
        "links_cache": { "type": ["string", "null"] }
      }
    },

    "Work": {
      "description": "Основная позиция Work (содержит вложенные Resource)",
      "type": "object",
      "allOf": [
        { "$ref": "#/$defs/PositionLineFields" }
      ],
      "required": [
        "raw_name", "raw_unit", "raw_quantity_formula", "raw_comment",
        "type", "style_manager", "status_correct", "status_calculated",
        "links", "resources"
      ],
      "properties": {
        "resources": {
          "type": "array",
          "items": { "$ref": "#/$defs/Resource" }
        }
      },
      "unevaluatedProperties": false
    },

    "Resource": {
      "description": "Вложенная ценообразующая позиция Resource",
      "type": "object",
      "allOf": [
        { "$ref": "#/$defs/PositionLineFields" }
      ],
      "required": [
        "raw_name", "raw_unit", "raw_quantity_formula", "raw_comment",
        "type", "style_manager", "status_correct", "status_calculated",
        "links"
      ],
      "unevaluatedProperties": false
    }
  }
}
"""