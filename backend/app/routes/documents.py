from flask import Blueprint, request, jsonify, abort, send_file
from flask_login import current_user

from app.extensions import db
from app.models import ServiceRequest, RequestDocument
from app.security.authz import login_required_api, can_access_service_request, can_manage_service_request, can_access_document
from app.services.audit import log_action
from app.utils.files import validate_and_store, resolve_safe_path, UploadRejected

bp = Blueprint("documents", __name__)

DOC_TYPES = {"report", "invoice", "photo", "other"}


@bp.post("/service-requests/<int:request_id>/documents")
@login_required_api
def upload_document(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_manage_service_request(sr) and current_user.role != "admin":
        abort(403)

    doc_type = request.form.get("doc_type", "other")
    if doc_type not in DOC_TYPES:
        doc_type = "other"

    meta = validate_and_store(request.files.get("file"), subdirectory=f"requests/{sr.id}/documents")
    doc = RequestDocument(
        service_request_id=sr.id, uploaded_by=current_user.id, doc_type=doc_type,
        file_path=meta["file_path"], original_filename=meta["original_filename"],
    )
    db.session.add(doc)
    log_action("upload_document", "request_document", None, details=f"request={sr.id}")
    db.session.commit()
    return jsonify({"document": doc.to_dict()}), 201


@bp.get("/service-requests/<int:request_id>/documents")
@login_required_api
def list_documents(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_access_service_request(sr):
        abort(403)
    docs = RequestDocument.query.filter_by(service_request_id=sr.id).all()
    return jsonify({"items": [d.to_dict() for d in docs]})


@bp.get("/documents/<int:document_id>/download")
@login_required_api
def download_document(document_id):
    doc = RequestDocument.query.get_or_404(document_id)
    if not can_access_document(doc):
        abort(403)
    try:
        path = resolve_safe_path(doc.file_path)
    except UploadRejected:
        abort(404)
    log_action("download_document", "request_document", doc.id)
    db.session.commit()
    return send_file(path, as_attachment=True, download_name=doc.original_filename)
