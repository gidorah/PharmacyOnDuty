// Wrap a plain validator as a Standard Schema, for Sandcastle's structured
// output. Copied from Sandcastle v0.12.0 (agent-workflows/shared/common.ts).

import type { StandardSchemaV1 } from "@standard-schema/spec";

export const standardSchema = <T>(validate: (value: unknown) => T): StandardSchemaV1<unknown, T> => ({
  "~standard": {
    version: 1,
    vendor: "pharmacyonduty-factory",
    validate: (value: unknown) => {
      try {
        return { value: validate(value) };
      } catch (error) {
        return { issues: [{ message: error instanceof Error ? error.message : "Validation failed" }] };
      }
    },
  },
});
