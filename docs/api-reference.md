# CrewAI Enterprise Pipeline

## Overview

- Version: `0.1.0`
- OpenAPI spec: `/api/v1/openapi.json`
- Interactive docs: `/api/v1/docs`

## Endpoints

### `GET /api/v1/admin/audit-log`

- Operation ID: `list_audit_logs_api_v1_admin_audit_log_get`
- Tags: `admin`
- Summary: List Audit Logs

**Parameters**

- `skip` (query, integer, optional)
- `limit` (query, integer, optional)
- `org_id` (query, object, optional)
- `action` (query, object, optional)
- `resource_type` (query, object, optional)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/admin/system/dependencies`

- Operation ID: `list_dependency_statuses_api_v1_admin_system_dependencies_get`
- Tags: `admin`
- Summary: List Dependency Statuses

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/admin/system/dependencies/refresh`

- Operation ID: `refresh_dependency_statuses_api_v1_admin_system_dependencies_refresh_post`
- Tags: `admin`
- Summary: Refresh Dependency Statuses

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/admin/system/llm/default`

- Operation ID: `get_runtime_llm_default_api_v1_admin_system_llm_default_get`
- Tags: `admin`
- Summary: Get Runtime Llm Default

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `PATCH /api/v1/admin/system/llm/default`

- Operation ID: `update_runtime_llm_default_api_v1_admin_system_llm_default_patch`
- Tags: `admin`
- Summary: Update Runtime Llm Default

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/OrgLlmRuntimeConfigUpdate`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/admin/system/llm/providers`

- Operation ID: `list_runtime_llm_providers_api_v1_admin_system_llm_providers_get`
- Tags: `admin`
- Summary: List Runtime Llm Providers

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/auth/token`

- Operation ID: `issue_token_api_v1_auth_token_post`
- Tags: `auth`
- Summary: Issue Token

**Parameters**

None

**Request Body**

- `application/json` -> `#/components/schemas/TokenRequest`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases`

- Operation ID: `list_cases_api_v1_cases_get`
- Tags: `cases`
- Summary: List Cases

**Parameters**

- `skip` (query, integer, optional)
- `limit` (query, integer, optional)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases`

- Operation ID: `create_case_api_v1_cases_post`
- Tags: `cases`
- Summary: Create Case

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/CaseCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `DELETE /api/v1/cases/{case_id}`

- Operation ID: `delete_case_api_v1_cases__case_id__delete`
- Tags: `cases`
- Summary: Delete Case

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `204`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}`

- Operation ID: `get_case_api_v1_cases__case_id__get`
- Tags: `cases`
- Summary: Get Case

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `PATCH /api/v1/cases/{case_id}`

- Operation ID: `update_case_api_v1_cases__case_id__patch`
- Tags: `cases`
- Summary: Update Case

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/CaseUpdate`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/approvals`

- Operation ID: `list_approvals_api_v1_cases__case_id__approvals_get`
- Tags: `cases`
- Summary: List Approvals

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/approvals/review`

- Operation ID: `review_case_api_v1_cases__case_id__approvals_review_post`
- Tags: `cases`
- Summary: Review Case

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/ApprovalDecisionCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/bfsi-nbfc-metrics`

- Operation ID: `get_bfsi_nbfc_metrics_api_v1_cases__case_id__bfsi_nbfc_metrics_get`
- Tags: `cases`
- Summary: Get Bfsi Nbfc Metrics

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the BFSI/NBFC sector engine are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/borrower-scorecard`

- Operation ID: `get_borrower_scorecard_api_v1_cases__case_id__borrower_scorecard_get`
- Tags: `cases`
- Summary: Get Borrower Scorecard

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the credit motion-pack engine are updated before the borrower scorecard is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/buy-side-analysis`

- Operation ID: `get_buy_side_analysis_api_v1_cases__case_id__buy_side_analysis_get`
- Tags: `cases`
- Summary: Get Buy Side Analysis

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the buy-side motion-pack engine are updated before the analysis is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/checklist`

- Operation ID: `list_checklist_items_api_v1_cases__case_id__checklist_get`
- Tags: `cases`
- Summary: List Checklist Items

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/checklist`

- Operation ID: `create_checklist_item_api_v1_cases__case_id__checklist_post`
- Tags: `cases`
- Summary: Create Checklist Item

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/ChecklistItemCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/checklist/seed`

- Operation ID: `seed_checklist_api_v1_cases__case_id__checklist_seed_post`
- Tags: `cases`
- Summary: Seed Checklist

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `PATCH /api/v1/cases/{case_id}/checklist/{item_id}`

- Operation ID: `update_checklist_item_api_v1_cases__case_id__checklist__item_id__patch`
- Tags: `cases`
- Summary: Update Checklist Item

**Parameters**

- `case_id` (path, string, required)
- `item_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/ChecklistItemUpdate`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/commercial-summary`

- Operation ID: `get_commercial_summary_api_v1_cases__case_id__commercial_summary_get`
- Tags: `cases`
- Summary: Get Commercial Summary

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the commercial engine are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/compliance-matrix`

- Operation ID: `get_compliance_matrix_api_v1_cases__case_id__compliance_matrix_get`
- Tags: `cases`
- Summary: Get Compliance Matrix

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the regulatory engine are updated before the compliance matrix is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/coverage`

- Operation ID: `get_coverage_api_v1_cases__case_id__coverage_get`
- Tags: `cases`
- Summary: Get Coverage

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/cyber-summary`

- Operation ID: `get_cyber_summary_api_v1_cases__case_id__cyber_summary_get`
- Tags: `cases`
- Summary: Get Cyber Summary

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the cyber/privacy engine are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/documents`

- Operation ID: `list_documents_api_v1_cases__case_id__documents_get`
- Tags: `cases`
- Summary: List Documents

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/documents`

- Operation ID: `create_document_api_v1_cases__case_id__documents_post`
- Tags: `cases`
- Summary: Create Document

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/DocumentArtifactCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/documents/upload`

- Operation ID: `upload_document_api_v1_cases__case_id__documents_upload_post`
- Tags: `cases`
- Summary: Upload Document

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `multipart/form-data` -> `#/components/schemas/Body_upload_document_api_v1_cases__case_id__documents_upload_post`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `DELETE /api/v1/cases/{case_id}/documents/{doc_id}`

- Operation ID: `delete_document_api_v1_cases__case_id__documents__doc_id__delete`
- Tags: `cases`
- Summary: Delete Document

**Parameters**

- `case_id` (path, string, required)
- `doc_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `204`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/documents/{doc_id}`

- Operation ID: `get_document_api_v1_cases__case_id__documents__doc_id__get`
- Tags: `cases`
- Summary: Get Document

**Parameters**

- `case_id` (path, string, required)
- `doc_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/documents/{doc_id}/chunks`

- Operation ID: `list_chunks_api_v1_cases__case_id__documents__doc_id__chunks_get`
- Tags: `cases`
- Summary: List Chunks

**Parameters**

- `case_id` (path, string, required)
- `doc_id` (path, string, required)
- `skip` (query, integer, optional)
- `limit` (query, integer, optional)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/evidence`

- Operation ID: `list_evidence_api_v1_cases__case_id__evidence_get`
- Tags: `cases`
- Summary: List Evidence

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/evidence`

- Operation ID: `create_evidence_api_v1_cases__case_id__evidence_post`
- Tags: `cases`
- Summary: Create Evidence

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/EvidenceItemCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/evidence/conflicts`

- Operation ID: `detect_evidence_conflicts_api_v1_cases__case_id__evidence_conflicts_get`
- Tags: `cases`
- Summary: Detect Evidence Conflicts

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/evidence/{evidence_id}`

- Operation ID: `get_evidence_api_v1_cases__case_id__evidence__evidence_id__get`
- Tags: `cases`
- Summary: Get Evidence

**Parameters**

- `case_id` (path, string, required)
- `evidence_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `PATCH /api/v1/cases/{case_id}/evidence/{evidence_id}`

- Operation ID: `update_evidence_api_v1_cases__case_id__evidence__evidence_id__patch`
- Tags: `cases`
- Summary: Update Evidence

**Parameters**

- `case_id` (path, string, required)
- `evidence_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/EvidenceItemUpdate`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/financial-summary`

- Operation ID: `get_financial_summary_api_v1_cases__case_id__financial_summary_get`
- Tags: `cases`
- Summary: Get Financial Summary

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the parsed financial package are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/forensic-flags`

- Operation ID: `get_forensic_flags_api_v1_cases__case_id__forensic_flags_get`
- Tags: `cases`
- Summary: Get Forensic Flags

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the forensic engine are updated before the flags are returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/issues`

- Operation ID: `list_issues_api_v1_cases__case_id__issues_get`
- Tags: `cases`
- Summary: List Issues

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/issues`

- Operation ID: `create_issue_api_v1_cases__case_id__issues_post`
- Tags: `cases`
- Summary: Create Issue

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/IssueRegisterItemCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/issues/scan`

- Operation ID: `scan_issues_api_v1_cases__case_id__issues_scan_post`
- Tags: `cases`
- Summary: Scan Issues

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `DELETE /api/v1/cases/{case_id}/issues/{issue_id}`

- Operation ID: `delete_issue_api_v1_cases__case_id__issues__issue_id__delete`
- Tags: `cases`
- Summary: Delete Issue

**Parameters**

- `case_id` (path, string, required)
- `issue_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `204`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/issues/{issue_id}`

- Operation ID: `get_issue_api_v1_cases__case_id__issues__issue_id__get`
- Tags: `cases`
- Summary: Get Issue

**Parameters**

- `case_id` (path, string, required)
- `issue_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `PATCH /api/v1/cases/{case_id}/issues/{issue_id}`

- Operation ID: `update_issue_api_v1_cases__case_id__issues__issue_id__patch`
- Tags: `cases`
- Summary: Update Issue

**Parameters**

- `case_id` (path, string, required)
- `issue_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/IssueUpdate`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/legal-summary`

- Operation ID: `get_legal_summary_api_v1_cases__case_id__legal_summary_get`
- Tags: `cases`
- Summary: Get Legal Summary

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the legal engine are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/manufacturing-metrics`

- Operation ID: `get_manufacturing_metrics_api_v1_cases__case_id__manufacturing_metrics_get`
- Tags: `cases`
- Summary: Get Manufacturing Metrics

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the Manufacturing sector engine are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/operations-summary`

- Operation ID: `get_operations_summary_api_v1_cases__case_id__operations_summary_get`
- Tags: `cases`
- Summary: Get Operations Summary

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the operations engine are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/qa`

- Operation ID: `list_qa_items_api_v1_cases__case_id__qa_get`
- Tags: `cases`
- Summary: List Qa Items

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/qa`

- Operation ID: `create_qa_item_api_v1_cases__case_id__qa_post`
- Tags: `cases`
- Summary: Create Qa Item

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/QaItemCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `PATCH /api/v1/cases/{case_id}/qa/{item_id}`

- Operation ID: `update_qa_item_api_v1_cases__case_id__qa__item_id__patch`
- Tags: `cases`
- Summary: Update Qa Item

**Parameters**

- `case_id` (path, string, required)
- `item_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/QaItemUpdate`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/reports/executive-memo`

- Operation ID: `get_executive_memo_api_v1_cases__case_id__reports_executive_memo_get`
- Tags: `cases`
- Summary: Get Executive Memo

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/reports/financial-annex`

- Operation ID: `get_financial_annex_markdown_api_v1_cases__case_id__reports_financial_annex_get`
- Tags: `cases`
- Summary: Get Financial Annex Markdown

**Parameters**

- `case_id` (path, string, required)
- `report_template` (query, #/components/schemas/ReportTemplateKind, optional)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/reports/full-report`

- Operation ID: `get_full_report_markdown_api_v1_cases__case_id__reports_full_report_get`
- Tags: `cases`
- Summary: Get Full Report Markdown

**Parameters**

- `case_id` (path, string, required)
- `report_template` (query, #/components/schemas/ReportTemplateKind, optional)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/requests`

- Operation ID: `list_requests_api_v1_cases__case_id__requests_get`
- Tags: `cases`
- Summary: List Requests

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/requests`

- Operation ID: `create_request_item_api_v1_cases__case_id__requests_post`
- Tags: `cases`
- Summary: Create Request Item

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/RequestItemCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `PATCH /api/v1/cases/{case_id}/requests/{item_id}`

- Operation ID: `update_request_item_api_v1_cases__case_id__requests__item_id__patch`
- Tags: `cases`
- Summary: Update Request Item

**Parameters**

- `case_id` (path, string, required)
- `item_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/RequestItemUpdate`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/runs`

- Operation ID: `list_runs_api_v1_cases__case_id__runs_get`
- Tags: `cases`
- Summary: List Runs

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/runs`

- Operation ID: `execute_run_api_v1_cases__case_id__runs_post`
- Tags: `cases`
- Summary: Execute Run

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/WorkflowRunCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/runs/{run_id}`

- Operation ID: `get_run_api_v1_cases__case_id__runs__run_id__get`
- Tags: `cases`
- Summary: Get Run

**Parameters**

- `case_id` (path, string, required)
- `run_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/runs/{run_id}/export-package`

- Operation ID: `create_run_export_package_api_v1_cases__case_id__runs__run_id__export_package_post`
- Tags: `cases`
- Summary: Create Run Export Package

**Parameters**

- `case_id` (path, string, required)
- `run_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/RunExportPackageCreate`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/runs/{run_id}/export-packages/{package_id}/download`

- Operation ID: `download_export_package_api_v1_cases__case_id__runs__run_id__export_packages__package_id__download_get`
- Tags: `cases`
- Summary: Download Export Package

**Parameters**

- `case_id` (path, string, required)
- `run_id` (path, string, required)
- `package_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/runs/{run_id}/report-bundles/{bundle_id}/download`

- Operation ID: `download_report_bundle_api_v1_cases__case_id__runs__run_id__report_bundles__bundle_id__download_get`
- Tags: `cases`
- Summary: Download Report Bundle

**Parameters**

- `case_id` (path, string, required)
- `run_id` (path, string, required)
- `bundle_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/runs/{run_id}/stream`

- Operation ID: `stream_run_progress_api_v1_cases__case_id__runs__run_id__stream_get`
- Tags: `cases`
- Summary: Stream Run Progress

**Parameters**

- `case_id` (path, string, required)
- `run_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/search`

- Operation ID: `search_evidence_api_v1_cases__case_id__search_post`
- Tags: `cases`
- Summary: Search Evidence

**Parameters**

- `case_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/SearchRequest`

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `POST /api/v1/cases/{case_id}/source-adapters/{adapter_id}/fetch`

- Operation ID: `fetch_from_source_adapter_api_v1_cases__case_id__source_adapters__adapter_id__fetch_post`
- Tags: `cases`
- Summary: Fetch From Source Adapter

**Parameters**

- `case_id` (path, string, required)
- `adapter_id` (path, string, required)
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

- `application/json` -> `#/components/schemas/SourceAdapterFetchRequest`

**Responses**

- `201`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/tax-summary`

- Operation ID: `get_tax_summary_api_v1_cases__case_id__tax_summary_get`
- Tags: `cases`
- Summary: Get Tax Summary

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the tax engine are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/tech-saas-metrics`

- Operation ID: `get_tech_saas_metrics_api_v1_cases__case_id__tech_saas_metrics_get`
- Tags: `cases`
- Summary: Get Tech Saas Metrics

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the Tech/SaaS sector engine are updated before the summary is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/cases/{case_id}/vendor-risk-tier`

- Operation ID: `get_vendor_risk_tier_api_v1_cases__case_id__vendor_risk_tier_get`
- Tags: `cases`
- Summary: Get Vendor Risk Tier

**Parameters**

- `case_id` (path, string, required)
- `persist_checklist` (query, boolean, optional): When true, checklist items satisfied by the vendor motion-pack engine are updated before the vendor tier analysis is returned.
- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/health/liveness`

- Operation ID: `liveness_api_v1_health_liveness_get`
- Tags: `health`
- Summary: Liveness

**Parameters**

None

**Request Body**

None

**Responses**

- `200`: Successful Response

### `GET /api/v1/health/readiness`

- Operation ID: `readiness_snapshot_api_v1_health_readiness_get`
- Tags: `health`
- Summary: Readiness Snapshot

**Parameters**

None

**Request Body**

None

**Responses**

- `200`: Successful Response

### `GET /api/v1/metrics`

- Operation ID: `metrics_api_v1_metrics_get`
- Tags: `health`
- Summary: Metrics

**Parameters**

None

**Request Body**

None

**Responses**

- `200`: Successful Response

### `GET /api/v1/source-adapters`

- Operation ID: `list_source_adapters_api_v1_source_adapters_get`
- Tags: `source-adapters`
- Summary: List Source Adapters

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/system/dependencies`

- Operation ID: `list_system_dependencies_api_v1_system_dependencies_get`
- Tags: `system`
- Summary: List System Dependencies

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/system/health`

- Operation ID: `health_api_v1_system_health_get`
- Tags: `system`
- Summary: Health

**Parameters**

None

**Request Body**

None

**Responses**

- `200`: Successful Response

### `GET /api/v1/system/llm/default`

- Operation ID: `get_llm_default_api_v1_system_llm_default_get`
- Tags: `system`
- Summary: Get Llm Default

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/system/llm/providers`

- Operation ID: `list_llm_providers_api_v1_system_llm_providers_get`
- Tags: `system`
- Summary: List Llm Providers

**Parameters**

- `Authorization` (header, object, optional)
- `X-CEP-User-Id` (header, object, optional)
- `X-CEP-User-Name` (header, object, optional)
- `X-CEP-User-Email` (header, object, optional)
- `X-CEP-User-Role` (header, object, optional)
- `X-CEP-Org-Id` (header, object, optional)

**Request Body**

None

**Responses**

- `200`: Successful Response
- `422`: Validation Error

### `GET /api/v1/system/overview`

- Operation ID: `overview_api_v1_system_overview_get`
- Tags: `system`
- Summary: Overview

**Parameters**

None

**Request Body**

None

**Responses**

- `200`: Successful Response

### `GET /api/v1/system/readiness`

- Operation ID: `readiness_api_v1_system_readiness_get`
- Tags: `system`
- Summary: Readiness

**Parameters**

None

**Request Body**

None

**Responses**

- `200`: Successful Response
