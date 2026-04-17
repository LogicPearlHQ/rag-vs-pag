Given a FOIA request and agency name, extract boolean facts that are
relevant to likely FOIA exemptions.

Return strict JSON:

```json
{
  "features": {
    "request_for_law_enforcement_investigation_records": true
  },
  "evidence": {
    "request_for_law_enforcement_investigation_records": "short quote or paraphrase"
  },
  "uncertain_features": []
}
```

Do not decide the exemption. Only extract facts from the request text.
If the request implies a record category by common FOIA usage, mark the
feature true and cite the phrase that supports the inference.
