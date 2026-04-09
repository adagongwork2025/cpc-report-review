"""
偵測記錄業務邏輯
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import DetectionLog, ReviewState
from datetime import date as DateType


def get_logs_with_review_status(db: Session, date: str, category: str):
    """
    取得指定日期和類別的偵測記錄，包含審核狀態

    Args:
        db: 資料庫 session
        date: 日期字串（YYYY-MM-DD）
        category: 類別（高處作業、局限空間）

    Returns:
        list: 偵測記錄列表，包含審核狀態
    """
    # 解析日期
    date_obj = DateType.fromisoformat(date)

    # 查詢偵測記錄
    logs = db.query(DetectionLog).filter(
        and_(
            DetectionLog.date == date_obj,
            DetectionLog.category == category
        )
    ).order_by(DetectionLog.detection_time.desc()).all()

    # 組合審核狀態
    result = []
    for log in logs:
        log_dict = log.to_dict()

        # 取得審核狀態
        if log.review_state:
            log_dict['review_status'] = log.review_state.status
            log_dict['note'] = log.review_state.note
        else:
            log_dict['review_status'] = 'pending'
            log_dict['note'] = None

        result.append(log_dict)

    return result


def get_all_dates_with_stats(db: Session, year: int = None, month: int = None):
    """
    取得所有有資料的日期列表及統計

    Args:
        db: 資料庫 session
        year: 年份（選填）
        month: 月份（選填）

    Returns:
        list: 日期列表及統計資訊
    """
    from sqlalchemy import func

    query = db.query(
        DetectionLog.date,
        DetectionLog.category,
        func.count(DetectionLog.id).label('total_items')
    ).group_by(
        DetectionLog.date,
        DetectionLog.category
    )

    # 篩選年月
    if year:
        query = query.filter(func.extract('year', DetectionLog.date) == year)
    if month:
        query = query.filter(func.extract('month', DetectionLog.date) == month)

    results = query.order_by(DetectionLog.date.desc()).all()

    # 組合統計資訊
    output = []
    for row in results:
        date_str = row.date.isoformat()
        category = row.category
        total = row.total_items

        # 查詢審核統計
        stats = db.query(
            func.count(ReviewState.id).label('total'),
            func.sum(func.case((ReviewState.status == 'confirmed', 1), else_=0)).label('confirmed'),
            func.sum(func.case((ReviewState.status == 'deleted', 1), else_=0)).label('deleted')
        ).filter(
            and_(
                ReviewState.date == row.date,
                ReviewState.category == category
            )
        ).first()

        confirmed_count = int(stats.confirmed or 0)
        deleted_count = int(stats.deleted or 0)
        pending_count = total - confirmed_count - deleted_count

        output.append({
            "date": date_str,
            "category": category,
            "total_items": total,
            "confirmed_count": confirmed_count,
            "deleted_count": deleted_count,
            "pending_count": pending_count,
            "reviewed": confirmed_count > 0 or deleted_count > 0
        })

    return output
