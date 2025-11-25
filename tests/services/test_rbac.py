"""Unit tests for role-based access control (RBAC)"""

import uuid

from sqlalchemy.orm import Session

from app.models.project import UserProject
from app.services.project import (
    add_user_to_project,
    get_user_role_in_project,
    is_user_in_project,
    update_user_role_in_project,
)
from tests.factories import ProjectFactory, UserFactory, UserProjectFactory


class TestOwnerRolePermissions:
    """Tests for owner role permissions (full access)"""

    def test_owner_can_add_members(self, db_session: Session):
        """Test that owner can add members to project"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        new_member = UserFactory.create(db_session)

        # Owner adds member
        user_project = add_user_to_project(
            db_session,
            project.id,
            new_member.id,
            role="member",
            added_by_user_id=owner.id,
        )

        assert user_project is not None
        assert user_project.user_id == new_member.id
        assert user_project.role == "member"

    def test_owner_can_remove_members(self, db_session: Session):
        """Test that owner can remove members from project"""
        from app.services.project import remove_user_from_project

        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Owner removes member
        result = remove_user_from_project(
            db_session,
            project.id,
            member.id,
            removed_by_user_id=owner.id,
        )

        assert result is True
        # Verify member is removed
        assert not is_user_in_project(db_session, project.id, member.id)

    def test_owner_can_change_member_roles(self, db_session: Session):
        """Test that owner can change member roles"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Owner changes member role to admin
        user_project = update_user_role_in_project(
            db_session,
            project.id,
            member.id,
            new_role="admin",
            actor_user_id=owner.id,
        )

        assert user_project is not None
        assert user_project.role == "admin"

    def test_owner_can_promote_to_owner(self, db_session: Session):
        """Test that owner can promote member to owner"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Owner promotes member to owner
        user_project = update_user_role_in_project(
            db_session,
            project.id,
            member.id,
            new_role="owner",
            actor_user_id=owner.id,
        )

        assert user_project.role == "owner"

    def test_owner_has_full_access_to_project(self, db_session: Session):
        """Test that owner has full access to project"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)

        # Verify owner is in project with owner role
        assert is_user_in_project(db_session, project.id, owner.id)
        role = get_user_role_in_project(db_session, project.id, owner.id)
        assert role == "owner"

    def test_owner_can_add_multiple_members(self, db_session: Session):
        """Test that owner can add multiple members"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        members = UserFactory.create_batch(db_session, count=3)

        # Owner adds multiple members
        for member in members:
            user_project = add_user_to_project(
                db_session,
                project.id,
                member.id,
                role="member",
                added_by_user_id=owner.id,
            )
            assert user_project is not None

        # Verify all members are in project
        for member in members:
            assert is_user_in_project(db_session, project.id, member.id)


class TestAdminRolePermissions:
    """Tests for admin role permissions (project management)"""

    def test_admin_can_add_members(self, db_session: Session):
        """Test that admin can add members to project"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        admin = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=admin, project=project, role="admin")
        new_member = UserFactory.create(db_session)

        # Admin adds member
        user_project = add_user_to_project(
            db_session,
            project.id,
            new_member.id,
            role="member",
            added_by_user_id=admin.id,
        )

        assert user_project is not None
        assert user_project.user_id == new_member.id

    def test_admin_can_remove_members(self, db_session: Session):
        """Test that admin can remove members from project"""
        from app.services.project import remove_user_from_project

        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        admin = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=admin, project=project, role="admin")
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Admin removes member
        result = remove_user_from_project(
            db_session,
            project.id,
            member.id,
            removed_by_user_id=admin.id,
        )

        assert result is True
        assert not is_user_in_project(db_session, project.id, member.id)

    def test_admin_can_change_member_roles(self, db_session: Session):
        """Test that admin can change member roles"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        admin = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=admin, project=project, role="admin")
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Admin changes member role to viewer
        user_project = update_user_role_in_project(
            db_session,
            project.id,
            member.id,
            new_role="viewer",
            actor_user_id=admin.id,
        )

        assert user_project.role == "viewer"

    def test_admin_role_is_in_project(self, db_session: Session):
        """Test that admin is in project with admin role"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        admin = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=admin, project=project, role="admin")

        assert is_user_in_project(db_session, project.id, admin.id)
        role = get_user_role_in_project(db_session, project.id, admin.id)
        assert role == "admin"


class TestMemberRolePermissions:
    """Tests for member role permissions (limited access)"""

    def test_member_is_in_project(self, db_session: Session):
        """Test that member is in project with member role"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        assert is_user_in_project(db_session, project.id, member.id)
        role = get_user_role_in_project(db_session, project.id, member.id)
        assert role == "member"

    def test_member_role_persists(self, db_session: Session):
        """Test that member role is persisted correctly"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Retrieve and verify role
        role = get_user_role_in_project(db_session, project.id, member.id)
        assert role == "member"

    def test_member_can_be_promoted_to_admin(self, db_session: Session):
        """Test that member can be promoted to admin"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Owner promotes member to admin
        user_project = update_user_role_in_project(
            db_session,
            project.id,
            member.id,
            new_role="admin",
            actor_user_id=owner.id,
        )

        assert user_project.role == "admin"

    def test_member_can_be_demoted_to_viewer(self, db_session: Session):
        """Test that member can be demoted to viewer"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Owner demotes member to viewer
        user_project = update_user_role_in_project(
            db_session,
            project.id,
            member.id,
            new_role="viewer",
            actor_user_id=owner.id,
        )

        assert user_project.role == "viewer"


class TestViewerRolePermissions:
    """Tests for viewer role permissions (read-only access)"""

    def test_viewer_is_in_project(self, db_session: Session):
        """Test that viewer is in project with viewer role"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        viewer = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=viewer, project=project, role="viewer")

        assert is_user_in_project(db_session, project.id, viewer.id)
        role = get_user_role_in_project(db_session, project.id, viewer.id)
        assert role == "viewer"

    def test_viewer_role_persists(self, db_session: Session):
        """Test that viewer role is persisted correctly"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        viewer = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=viewer, project=project, role="viewer")

        # Retrieve and verify role
        role = get_user_role_in_project(db_session, project.id, viewer.id)
        assert role == "viewer"

    def test_viewer_can_be_promoted_to_member(self, db_session: Session):
        """Test that viewer can be promoted to member"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        viewer = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=viewer, project=project, role="viewer")

        # Owner promotes viewer to member
        user_project = update_user_role_in_project(
            db_session,
            project.id,
            viewer.id,
            new_role="member",
            actor_user_id=owner.id,
        )

        assert user_project.role == "member"

    def test_viewer_can_be_promoted_to_admin(self, db_session: Session):
        """Test that viewer can be promoted to admin"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        viewer = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=viewer, project=project, role="viewer")

        # Owner promotes viewer to admin
        user_project = update_user_role_in_project(
            db_session,
            project.id,
            viewer.id,
            new_role="admin",
            actor_user_id=owner.id,
        )

        assert user_project.role == "admin"


class TestPermissionInheritance:
    """Tests for permission inheritance from projects to resources"""

    def test_member_inherits_project_permissions(self, db_session: Session):
        """Test that member inherits permissions from project membership"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Verify member has access through project membership
        assert is_user_in_project(db_session, project.id, member.id)
        role = get_user_role_in_project(db_session, project.id, member.id)
        assert role == "member"

    def test_admin_inherits_project_permissions(self, db_session: Session):
        """Test that admin inherits permissions from project membership"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        admin = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=admin, project=project, role="admin")

        # Verify admin has access through project membership
        assert is_user_in_project(db_session, project.id, admin.id)
        role = get_user_role_in_project(db_session, project.id, admin.id)
        assert role == "admin"

    def test_viewer_inherits_project_permissions(self, db_session: Session):
        """Test that viewer inherits permissions from project membership"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        viewer = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=viewer, project=project, role="viewer")

        # Verify viewer has access through project membership
        assert is_user_in_project(db_session, project.id, viewer.id)
        role = get_user_role_in_project(db_session, project.id, viewer.id)
        assert role == "viewer"

    def test_role_change_updates_permissions(self, db_session: Session):
        """Test that changing role updates inherited permissions"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="viewer")

        # Verify initial role
        assert get_user_role_in_project(db_session, project.id, user.id) == "viewer"

        # Change role to member
        update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="member",
            actor_user_id=owner.id,
        )

        # Verify role is updated
        assert get_user_role_in_project(db_session, project.id, user.id) == "member"

    def test_removal_revokes_permissions(self, db_session: Session):
        """Test that removing user from project revokes permissions"""
        from app.services.project import remove_user_from_project

        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Verify member has access
        assert is_user_in_project(db_session, project.id, member.id)

        # Remove member from project
        remove_user_from_project(
            db_session,
            project.id,
            member.id,
            removed_by_user_id=owner.id,
        )

        # Verify member no longer has access
        assert not is_user_in_project(db_session, project.id, member.id)

    def test_multiple_roles_in_different_projects(self, db_session: Session):
        """Test that user can have different roles in different projects"""
        owner1 = UserFactory.create(db_session)
        owner2 = UserFactory.create(db_session)
        project1 = ProjectFactory.create(db_session, owner1)
        project2 = ProjectFactory.create(db_session, owner2)
        user = UserFactory.create(db_session)

        # Add user as member to project1
        UserProjectFactory.create(db_session, user=user, project=project1, role="member")

        # Add user as admin to project2
        UserProjectFactory.create(db_session, user=user, project=project2, role="admin")

        # Verify different roles in different projects
        assert get_user_role_in_project(db_session, project1.id, user.id) == "member"
        assert get_user_role_in_project(db_session, project2.id, user.id) == "admin"

    def test_permission_consistency_across_queries(self, db_session: Session):
        """Test that permissions are consistent across multiple queries"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Query multiple times and verify consistency
        role1 = get_user_role_in_project(db_session, project.id, member.id)
        role2 = get_user_role_in_project(db_session, project.id, member.id)
        role3 = get_user_role_in_project(db_session, project.id, member.id)

        assert role1 == role2 == role3 == "member"


class TestRoleTransitions:
    """Tests for valid role transitions"""

    def test_transition_viewer_to_member(self, db_session: Session):
        """Test transition from viewer to member"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="viewer")

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="member",
            actor_user_id=owner.id,
        )

        assert user_project.role == "member"

    def test_transition_member_to_admin(self, db_session: Session):
        """Test transition from member to admin"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="member")

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="admin",
            actor_user_id=owner.id,
        )

        assert user_project.role == "admin"

    def test_transition_admin_to_owner(self, db_session: Session):
        """Test transition from admin to owner"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="admin")

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="owner",
            actor_user_id=owner.id,
        )

        assert user_project.role == "owner"

    def test_transition_owner_to_admin(self, db_session: Session):
        """Test transition from owner to admin"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="owner")

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="admin",
            actor_user_id=owner.id,
        )

        assert user_project.role == "admin"

    def test_transition_admin_to_member(self, db_session: Session):
        """Test transition from admin to member"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="admin")

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="member",
            actor_user_id=owner.id,
        )

        assert user_project.role == "member"

    def test_transition_member_to_viewer(self, db_session: Session):
        """Test transition from member to viewer"""
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, owner)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="member")

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="viewer",
            actor_user_id=owner.id,
        )

        assert user_project.role == "viewer"
