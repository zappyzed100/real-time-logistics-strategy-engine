{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- set base_schema = (custom_schema_name | trim) if custom_schema_name is not none else default_schema -%}

    {{ base_schema }}
{%- endmacro %}
