from crewai_enterprise_pipeline_api.domain.models import (
    SourceAdapterCategory,
    SourceAdapterSummary,
)


def get_adapter_catalog() -> list[SourceAdapterSummary]:
    return [
        SourceAdapterSummary(
            adapter_key="uploaded_dataroom",
            category=SourceAdapterCategory.UPLOADED,
            title="Uploaded Data Room",
            purpose=(
                "Accept private diligence artifacts from secure uploads and "
                "operator-managed folders."
            ),
            supports_india=True,
            supports_live_credentials=False,
            fallback_mode="primary",
        ),
        SourceAdapterSummary(
            adapter_key="mca_public_records",
            category=SourceAdapterCategory.PUBLIC,
            title="MCA Public Records",
            purpose="Enrich Indian corporate diligence with public registry and filing context.",
            supports_india=True,
            supports_live_credentials=False,
            fallback_mode="fixture_or_manual_export",
        ),
        SourceAdapterSummary(
            adapter_key="listed_disclosures",
            category=SourceAdapterCategory.PUBLIC,
            title="Listed Company Disclosures",
            purpose=(
                "Capture listed-entity filings, disclosures, and exchange-linked "
                "evidence trails."
            ),
            supports_india=True,
            supports_live_credentials=False,
            fallback_mode="public_feed_or_uploaded_export",
        ),
        SourceAdapterSummary(
            adapter_key="vendor_connector",
            category=SourceAdapterCategory.VENDOR,
            title="Commercial Vendor Connector",
            purpose="Provide a production-shaped adapter slot for paid diligence and data vendors.",
            supports_india=True,
            supports_live_credentials=True,
            fallback_mode="public_fallback_and_fixtures",
        ),
    ]
