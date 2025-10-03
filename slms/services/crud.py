"""Generic CRUD service with activity logging and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type, TypeVar

from flask import g
from sqlalchemy.exc import IntegrityError

from slms.extensions import db
from slms.services.audit import log_admin_action

if TYPE_CHECKING:
    from flask_login import current_user

Model = TypeVar("Model", bound=db.Model)


class CRUDService:
    """Base CRUD service with common operations."""

    def __init__(self, model: Type[Model]):
        """
        Initialize CRUD service.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model
        self.model_name = model.__tablename__

    def create(self, data: dict[str, Any], user: Any = None, skip_log: bool = False) -> tuple[Model | None, str | None]:
        """
        Create a new record.

        Args:
            data: Dictionary of field values
            user: User performing the action (for logging)
            skip_log: Skip activity logging

        Returns:
            (created_object, error_message)
        """
        try:
            # Validate required fields
            error = self._validate_create(data)
            if error:
                return None, error

            # Create instance
            instance = self.model(**data)
            db.session.add(instance)
            db.session.flush()  # Get ID before commit

            # Log activity
            if not skip_log and user:
                log_admin_action(
                    user,
                    f"{self.model_name}_created",
                    self.model_name,
                    instance.id,
                    metadata={'data': self._sanitize_log_data(data)}
                )

            db.session.commit()
            return instance, None

        except IntegrityError as e:
            db.session.rollback()
            return None, self._handle_integrity_error(e)

        except Exception as e:
            db.session.rollback()
            from flask import current_app
            current_app.logger.error(f"Failed to create {self.model_name}: {e}")
            return None, f"Failed to create {self.model_name}"

    def get_by_id(self, object_id: str) -> Model | None:
        """Get record by ID (tenant-scoped)."""
        from slms.blueprints.common.tenant import org_query
        return org_query(self.model).filter_by(id=object_id).first()

    def list_all(self, filters: dict[str, Any] | None = None, order_by: Any = None) -> list[Model]:
        """
        List all records (tenant-scoped).

        Args:
            filters: Additional filter criteria
            order_by: SQLAlchemy order_by clause

        Returns:
            List of model instances
        """
        from slms.blueprints.common.tenant import org_query
        query = org_query(self.model)

        if filters:
            query = query.filter_by(**filters)

        if order_by is not None:
            query = query.order_by(order_by)

        return query.all()

    def update(self, object_id: str, data: dict[str, Any], user: Any = None, skip_log: bool = False) -> tuple[bool, str | None]:
        """
        Update a record.

        Args:
            object_id: ID of object to update
            data: Dictionary of fields to update
            user: User performing the action (for logging)
            skip_log: Skip activity logging

        Returns:
            (success, error_message)
        """
        try:
            instance = self.get_by_id(object_id)
            if not instance:
                return False, f"{self.model_name.capitalize()} not found"

            # Validate update
            error = self._validate_update(instance, data)
            if error:
                return False, error

            # Update fields
            for key, value in data.items():
                if hasattr(instance, key) and key not in ('id', 'created_at', 'updated_at', 'org_id'):
                    setattr(instance, key, value)

            # Log activity
            if not skip_log and user:
                log_admin_action(
                    user,
                    f"{self.model_name}_updated",
                    self.model_name,
                    object_id,
                    metadata={'data': self._sanitize_log_data(data)}
                )

            db.session.commit()
            return True, None

        except IntegrityError as e:
            db.session.rollback()
            return False, self._handle_integrity_error(e)

        except Exception as e:
            db.session.rollback()
            from flask import current_app
            current_app.logger.error(f"Failed to update {self.model_name}: {e}")
            return False, f"Failed to update {self.model_name}"

    def delete(self, object_id: str, user: Any = None, skip_log: bool = False) -> tuple[bool, str | None]:
        """
        Delete a record.

        Args:
            object_id: ID of object to delete
            user: User performing the action (for logging)
            skip_log: Skip activity logging

        Returns:
            (success, error_message)
        """
        try:
            instance = self.get_by_id(object_id)
            if not instance:
                return False, f"{self.model_name.capitalize()} not found"

            # Log activity before deletion
            if not skip_log and user:
                log_admin_action(
                    user,
                    f"{self.model_name}_deleted",
                    self.model_name,
                    object_id
                )

            db.session.delete(instance)
            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            from flask import current_app
            current_app.logger.error(f"Failed to delete {self.model_name}: {e}")
            return False, f"Failed to delete {self.model_name}"

    def bulk_create(self, items: list[dict[str, Any]], user: Any = None) -> tuple[list[Model], list[str]]:
        """
        Bulk create multiple records.

        Args:
            items: List of dictionaries with field values
            user: User performing the action

        Returns:
            (created_objects, errors)
        """
        created = []
        errors = []

        for idx, data in enumerate(items):
            instance, error = self.create(data, user, skip_log=True)
            if error:
                errors.append(f"Item {idx + 1}: {error}")
            else:
                created.append(instance)

        # Single bulk log entry
        if created and user:
            log_admin_action(
                user,
                f"{self.model_name}_bulk_created",
                self.model_name,
                metadata={'count': len(created), 'errors': len(errors)}
            )

        return created, errors

    def bulk_update(self, updates: dict[str, dict[str, Any]], user: Any = None) -> tuple[int, list[str]]:
        """
        Bulk update multiple records.

        Args:
            updates: Dictionary mapping object IDs to update data
            user: User performing the action

        Returns:
            (success_count, errors)
        """
        success_count = 0
        errors = []

        for object_id, data in updates.items():
            success, error = self.update(object_id, data, user, skip_log=True)
            if error:
                errors.append(f"ID {object_id}: {error}")
            else:
                success_count += 1

        # Single bulk log entry
        if success_count > 0 and user:
            log_admin_action(
                user,
                f"{self.model_name}_bulk_updated",
                self.model_name,
                metadata={'count': success_count, 'errors': len(errors)}
            )

        return success_count, errors

    def bulk_delete(self, object_ids: list[str], user: Any = None) -> tuple[int, list[str]]:
        """
        Bulk delete multiple records.

        Args:
            object_ids: List of object IDs to delete
            user: User performing the action

        Returns:
            (success_count, errors)
        """
        success_count = 0
        errors = []

        for object_id in object_ids:
            success, error = self.delete(object_id, user, skip_log=True)
            if error:
                errors.append(f"ID {object_id}: {error}")
            else:
                success_count += 1

        # Single bulk log entry
        if success_count > 0 and user:
            log_admin_action(
                user,
                f"{self.model_name}_bulk_deleted",
                self.model_name,
                metadata={'count': success_count, 'errors': len(errors)}
            )

        return success_count, errors

    def _validate_create(self, data: dict[str, Any]) -> str | None:
        """
        Validate data for creation.
        Override in subclasses for model-specific validation.

        Args:
            data: Data to validate

        Returns:
            Error message or None
        """
        return None

    def _validate_update(self, instance: Model, data: dict[str, Any]) -> str | None:
        """
        Validate data for update.
        Override in subclasses for model-specific validation.

        Args:
            instance: Instance being updated
            data: Update data

        Returns:
            Error message or None
        """
        return None

    def _handle_integrity_error(self, error: IntegrityError) -> str:
        """Convert database integrity errors to user-friendly messages."""
        error_msg = str(error)
        if 'unique' in error_msg.lower():
            return "A record with these values already exists"
        if 'foreign' in error_msg.lower():
            return "Referenced record does not exist"
        return "Database constraint violation"

    def _sanitize_log_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive fields from log data."""
        sensitive_fields = {'password', 'password_hash', 'secret', 'token', 'api_key'}
        return {k: v for k, v in data.items() if k not in sensitive_fields}


__all__ = ['CRUDService']
