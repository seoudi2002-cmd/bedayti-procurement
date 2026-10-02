"""Master-data reads. Anything personal (employees, contacts) is admin-only; branch/supplier listings expose
business attributes only."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require
from app.db import get_session
from app.models import (
    BranchContact, DimBranch, DimEmployee, DimRegion, DimSupplier, ImportBatch, SupplierContact,
)

router = APIRouter()


@router.get("/branches")
def list_branches(session: Session = Depends(get_session), _: Principal = Depends(require("viewer"))):
    headcount = dict(session.execute(select(DimEmployee.branch_id, func.count()).where(
        DimEmployee.branch_id.is_not(None)).group_by(DimEmployee.branch_id)).all())
    hr_batch = session.scalar(select(ImportBatch).where(
        ImportBatch.module_id == "employees", ImportBatch.status == "loaded").order_by(ImportBatch.id.desc()))
    regions = {r.id: r.name for r in session.scalars(select(DimRegion))}
    return {
        "headcount_source": "HR file (employees with a resolved branch)",
        "headcount_warnings": (hr_batch.warnings if hr_batch else None) or ([] if hr_batch else
                                                                         [{"code": "hr_not_loaded", "message": "HR file not loaded"}]),
        "branches": [{"id": b.id, "name_ar": b.name_ar, "name_en": b.name_en, "branch_type": b.branch_type,
                      "system_key": b.system_key, "code": b.code, "source_seq": b.source_seq,
                      "region": regions.get(b.region_id), "address": b.address,
                      "headcount_hr": headcount.get(b.id)}
                     for b in session.scalars(select(DimBranch).order_by(DimBranch.source_seq, DimBranch.id))],
    }


@router.get("/branches/{branch_id}/contact")
def branch_contact(branch_id: int, session: Session = Depends(get_session), _: Principal = Depends(require("admin"))):
    c = session.scalar(select(BranchContact).where(BranchContact.branch_id == branch_id))
    if c is None:
        raise HTTPException(404, "No contact record")
    emp = session.get(DimEmployee, c.manager_employee_id) if c.manager_employee_id else None
    return {"branch_id": branch_id, "branch_manager_name_source": c.branch_manager_name_source,
            "branch_phone": c.branch_phone, "manager_phone_1": c.manager_phone_1, "manager_phone_2": c.manager_phone_2,
            "region_manager_name_source": c.region_manager_name_source, "region_manager_phone": c.region_manager_phone,
            "email": c.email, "reconciliation_status": c.manager_reconciliation_status,
            "hr_employee": None if emp is None else {"employee_code": emp.employee_code, "full_name": emp.full_name,
                                                      "position_source": emp.position_source,
                                                      "branch_source_text": emp.branch_source_text}}


@router.get("/employees")
def list_employees(limit: int = 200, offset: int = 0, session: Session = Depends(get_session),
                   _: Principal = Depends(require("admin"))):
    return [{"employee_code": e.employee_code, "full_name": e.full_name, "hire_date": e.hire_date,
             "position_source": e.position_source, "branch_id": e.branch_id, "branch_source_text": e.branch_source_text,
             "branch_match_method": e.branch_match_method, "governorate_source": e.governorate_source,
             "governorate_issue": e.governorate_issue, "missing_fields": e.missing_fields}
            for e in session.scalars(select(DimEmployee).order_by(DimEmployee.employee_code).limit(min(limit, 1000)).offset(offset))]


@router.get("/suppliers")
def list_suppliers(session: Session = Depends(get_session), _: Principal = Depends(require("viewer"))):
    return [{"id": s.id, "code": s.code, "register_no": s.register_no, "name": s.name,
             "category_source": s.category_source, "services_source": s.services_source,
             "commercial_reg_no": s.commercial_reg_no, "tax_id": s.tax_id, "notes_source": s.notes_source}
            for s in session.scalars(select(DimSupplier).order_by(DimSupplier.code))]


@router.get("/suppliers/{supplier_id}/contact")
def supplier_contact(supplier_id: int, session: Session = Depends(get_session), _: Principal = Depends(require("admin"))):
    c = session.scalar(select(SupplierContact).where(SupplierContact.supplier_id == supplier_id))
    if c is None:
        raise HTTPException(404, "No contact record")
    return {"supplier_id": supplier_id, "contact_name_source": c.contact_name_source, "phone_source": c.phone_source,
            "email": c.email}
