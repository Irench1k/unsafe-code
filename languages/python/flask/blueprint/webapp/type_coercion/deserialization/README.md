# Unsafe Deserialization and Object Binding
Allowing attackers to pick the class or type used during deserialization lets them smuggle behavior, bypass validation, or even execute code.
## Overview

Flask apps that ingest JSON, YAML, or pickled data may hydrate payloads into Python objects automatically. Without strict schemas, those objects can come with unexpected defaults, mixins, or even executable code paths. Even when remote code execution is out of scope, binding user-controlled types to business logic often breaks authorization assumptions.

**Practice tips:** - Prefer explicit schema libraries that construct safe data structures, not arbitrary objects. - Keep deserialization code away from security decisions unless the payload has been validated. - Log rejected payloads so you see probing attempts early.
