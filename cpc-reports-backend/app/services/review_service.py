"""
審核業務邏輯
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import ReviewAction, ReviewState, DetectionLog
from datetime import datetime, date as DateType


def process_bulk_actions(db: Session, date: str, category: str, actions: list, reviewer_ip: str):
    """
    處理批次審核動作

    Args:
        db: 資料庫 session
        date: 日期字串（YYYY-MM-DD）
        category: 類別
        actions: 審核動作列表
        reviewer_ip: 審核人 IP

    Returns:
        dict: 處理結果統計
    """
    date_obj = DateType.fromisoformat(date)
    confirmed_count = 0
    deleted_count = 0

    for action_data in actions:
        detection_log_id = action_data['detection_log_id']
        action_type = action_data['action']
        note = action_data.get('note')

        # 1. 記錄審核動作（歷史）
        review_action = ReviewAction(
            detection_log_id=detection_log_id,
            date=date_obj,
            category=category,
            action=action_type,
            note=note,
            reviewer_ip=reviewer_ip,
            action_at=datetime.now()
        )
        db.add(review_action)

        # 2. 更新審核狀態（當前狀態）
        state = db.query(ReviewState).filter_by(
            detection_log_id=detection_log_id
        ).first()

        if state:
            # 更新現有狀態
            state.status = action_type
            state.note = note
            state.last_action_at = datetime.now()
        else:
            # 建立新狀態
            state = ReviewState(
                detection_log_id=detection_log_id,
                date=date_obj,
                category=category,
                status=action_type,
                note=note,
                last_action_at=datetime.now()
            )
            db.add(state)

        # 統計
        if action_type == 'confirmed':
            confirmed_count += 1
        elif action_type == 'deleted':
            deleted_count += 1

    db.commit()

    return {
        "processed": len(actions),
        "confirmed_count": confirmed_count,
        "deleted_count": deleted_count,
        "report_ready": confirmed_count > 0
    }


def get_review_summary(db: Session, date: str, category: str):
    """
    取得審核狀態摘要

    Args:
        db: 資料庫 session
        date: 日期字串（YYYY-MM-DD）
        category: 類別

    Returns:
        dict: 審核摘要統計
    """
    from sqlalchemy import func

    date_obj = DateType.fromisoformat(date)

    # 查詢統計
    stats = db.query(
        func.count(ReviewState.id).label('total'),
        func.sum(func.case((ReviewState.status == 'confirmed', 1), else_=0)).label('confirmed'),
        func.sum(func.case((ReviewState.status == 'deleted', 1), else_=0)).label('deleted'),
        func.sum(func.case((ReviewState.status == 'pending', 1), else_=0)).label('pending'),
        func.max(ReviewState.last_action_at).label('last_time')
    ).filter(
        and_(
            ReviewState.date == date_obj,
            ReviewState.category == category
        )
    ).first()

    return {
        "date": date,
        "category": category,
        "total_items": int(stats.total or 0),
        "confirmed_count": int(stats.confirmed or 0),
        "deleted_count": int(stats.deleted or 0),
        "pending_count": int(stats.pending or 0),
        "last_review_time": stats.last_time
    }


def get_report_data(db: Session, date: str, category: str):
    """
    取得已審核的報告資料（只包含 confirmed 的項目）

    Args:
        db: 資料庫 session
        date: 日期字串（YYYY-MM-DD）
        category: 類別

    Returns:
        dict: 報告資料
    """
    date_obj = DateType.fromisoformat(date)

    # 查詢已確認的偵測記錄
    logs = db.query(DetectionLog).join(ReviewState).filter(
        and_(
            ReviewState.date == date_obj,
            ReviewState.category == category,
            ReviewState.status == 'confirmed'
        )
    ).order_by(DetectionLog.detection_time.desc()).all()

    items = []
    for log in logs:
        item = log.to_dict()
        if log.review_state:
            item['note'] = log.review_state.note
            item['reviewed_at'] = log.review_state.last_action_at.isoformat() if log.review_state.last_action_at else None
        items.append(item)

    # 查詢最後審核時間
    last_review = db.query(ReviewState.last_action_at).filter(
        and_(
            ReviewState.date == date_obj,
            ReviewState.category == category,
            ReviewState.status == 'confirmed'
        )
    ).order_by(ReviewState.last_action_at.desc()).first()

    return {
        "date": date,
        "category": category,
        "total_confirmed": len(items),
        "reviewed": len(items) > 0,
        "last_review_time": last_review[0].isoformat() if last_review and last_review[0] else None,
        "items": items
    }
