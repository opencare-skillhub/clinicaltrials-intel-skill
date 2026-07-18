"""
将 UnifiedTrial 适配为 content_builder / 渠道可消费的「伪 CTGov study」结构。

只填充本仓库实际读取的路径，避免改动 GeWe/飞书代码。
注意：id 使用 ChiCTR 号；落地文件名需调用方自行 sanitize。
"""

from __future__ import annotations

from typing import Any

from lib.chictr.models import UnifiedTrial


def adapt_to_ctgov_study(trial: UnifiedTrial) -> dict[str, Any]:
    """UnifiedTrial → 伪 protocolSection study dict。"""
    nct_like = trial.id or "UNKNOWN"
    title = trial.title_cn or trial.title or nct_like
    conditions = [c for c in [trial.condition] if c]
    interventions = []
    if trial.intervention:
        interventions.append({"name": trial.intervention, "type": "OTHER"})

    status = trial.status or "UNKNOWN"
    # 粗映射中文状态
    status_map = {
        "招募中": "RECRUITING",
        "正在招募": "RECRUITING",
        "尚未招募": "NOT_YET_RECRUITING",
        "招募完成": "ACTIVE_NOT_RECRUITING",
        "已完成": "COMPLETED",
        "暂停": "SUSPENDED",
        "终止": "TERMINATED",
    }
    for k, v in status_map.items():
        if k in status:
            status = v
            break
    status_u = status.upper() if status.isascii() else status

    locations = []
    if trial.institution:
        locations.append(
            {
                "facility": trial.institution,
                "city": "",
                "country": "China",
            }
        )

    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_like,
                "briefTitle": title,
                "officialTitle": trial.title or title,
            },
            "statusModule": {
                "overallStatus": status_u,
                "startDateStruct": {"date": trial.registration_date or ""},
                "lastUpdatePostDateStruct": {"date": trial.last_update or trial.registration_date or ""},
                "studyFirstPostDateStruct": {"date": trial.registration_date or ""},
            },
            "conditionsModule": {
                "conditions": conditions or [],
            },
            "armsInterventionsModule": {
                "interventions": interventions,
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": trial.sponsor or trial.institution or ""},
            },
            "designModule": {
                "phases": [trial.phase] if trial.phase else [],
                "studyType": trial.study_type or "",
            },
            "contactsLocationsModule": {
                "locations": locations,
            },
            "descriptionModule": {
                "briefSummary": f"来源: {trial.source}; URL: {trial.url}",
            },
        },
        # 扩展字段：本仓库下游可忽略
        "_source": trial.source,
        "_source_url": trial.url,
        "_unified": trial.to_dict(),
    }


def adapt_many(trials: list[UnifiedTrial]) -> list[dict[str, Any]]:
    return [adapt_to_ctgov_study(t) for t in trials]
