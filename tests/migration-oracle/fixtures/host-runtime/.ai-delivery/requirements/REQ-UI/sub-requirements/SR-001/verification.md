<!-- ai-delivery-verification:review-rounds -->
<!-- ai-delivery-verification:commands-results -->
<!-- ai-delivery-verification:sign-off -->
<!-- ai-delivery-verification:contract:v2 -->
```json
{
  "version": 2,
  "subreq_id": "SR-001",
  "inputs": [
    {
      "path": ".ai-delivery/requirements/REQ-UI/sub-requirements/SR-001/design.md",
      "sha256": "88d4a9e3c735d50a4d8f0e64b46effcaada48bdba31faf61512c9eb116493232"
    }
  ],
  "checks": [
    {
      "id": "native",
      "acceptance_ids": [
        "AC-001"
      ],
      "required": true,
      "result": "passed",
      "mode": "executed",
      "command": "python3 -m unittest",
      "exit_code": 0,
      "evidence": [
        {
          "path": "native.log",
          "sha256": "1fb1e7f14870b28823dc4363b1fd641d5c9b315f1f385d2079308dddf6ea70c5"
        }
      ]
    }
  ],
  "reviews": [
    {
      "reviewer": "fixture-reviewer",
      "context": "fresh",
      "result": "clean",
      "input_sha256": "5add6ab42d4ec0598d44a08f28d9fd646ec7dc4441e90503ce3fb3e5b9f0ae18",
      "findings": [],
      "verification_sha256": "eb8f0e49c3a90c7291a180bd2640370a45c746a6e23df593e99cb92ccc6a7898"
    }
  ]
}
```
<!-- /ai-delivery-verification:contract:v2 -->
