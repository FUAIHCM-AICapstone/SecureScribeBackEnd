"""Integration tests for search workflows"""

from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.utils.auth import create_access_token
from tests.factories import FileFactory, MeetingFactory, ProjectFactory, UserFactory

fake = Faker()


class TestDocumentIndexingAndSearch:
    """Integration tests for document indexing and search workflow"""

    def test_search_dynamic_returns_matching_files(self, db_session: Session):
        """Test that dynamic search returns files matching search term"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create files with searchable names
        file1 = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="quarterly_report.pdf",
        )
        file2 = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="annual_summary.pdf",
        )
        file3 = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="quarterly_budget.pdf",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=quarterly&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        results = data["data"]
        assert len(results) >= 2

        # Verify results contain quarterly files
        filenames = [r["name"] for r in results]
        assert "quarterly_report.pdf" in filenames
        assert "quarterly_budget.pdf" in filenames

    def test_search_dynamic_returns_matching_projects(self, db_session: Session):
        """Test that dynamic search returns projects matching search term"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        # Create projects with searchable names
        project1 = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Marketing Campaign",
        )
        project2 = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Product Development",
        )
        project3 = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Marketing Analytics",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=Marketing&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        results = data["data"]
        assert len(results) >= 2

        # Verify results contain marketing projects
        names = [r["name"] for r in results]
        assert "Marketing Campaign" in names
        assert "Marketing Analytics" in names

    def test_search_dynamic_returns_matching_meetings(self, db_session: Session):
        """Test that dynamic search returns meetings matching search term"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        # Create meetings with searchable titles
        meeting1 = MeetingFactory.create(
            db_session,
            created_by=creator,
            title="Q4 Planning Session",
            is_personal=True,
        )
        meeting2 = MeetingFactory.create(
            db_session,
            created_by=creator,
            title="Team Standup",
            is_personal=True,
        )
        meeting3 = MeetingFactory.create(
            db_session,
            created_by=creator,
            title="Q4 Budget Review",
            is_personal=True,
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=Q4&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        results = data["data"]
        assert len(results) >= 2

        # Verify results contain Q4 meetings
        titles = [r["name"] for r in results]
        assert "Q4 Planning Session" in titles
        assert "Q4 Budget Review" in titles

    def test_search_dynamic_respects_access_control(self, db_session: Session):
        """Test that search respects access control and doesn't return inaccessible items"""
        # Arrange
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        db_session.commit()

        # Create project and file owned by creator
        project = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Secret Project",
        )
        file = FileFactory.create(
            db_session,
            uploaded_by=creator,
            filename="secret_document.pdf",
            project=project,
        )
        db_session.commit()

        # Search as other_user who doesn't have access
        access_token = create_access_token({"sub": str(other_user.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=Secret&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]

        # Should not contain the secret project or file
        names = [r["name"] for r in results]
        assert "Secret Project" not in names
        assert "secret_document.pdf" not in names

    def test_search_dynamic_includes_user_files(self, db_session: Session):
        """Test that search includes files uploaded by the user"""
        # Arrange
        user = UserFactory.create(db_session)
        db_session.commit()

        # Create file uploaded by user
        file = FileFactory.create(
            db_session,
            uploaded_by=user,
            filename="my_personal_file.pdf",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(user.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=personal&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]

        # Should contain the user's file
        filenames = [r["name"] for r in results]
        assert "my_personal_file.pdf" in filenames

    def test_search_dynamic_includes_project_member_files(self, db_session: Session):
        """Test that search includes files from projects user is member of"""
        # Arrange
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        db_session.commit()

        # Create project and add member
        project = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Team Project",
        )
        from app.services.project import add_user_to_project

        add_user_to_project(db_session, project.id, member.id, "member")

        # Create file in project
        file = FileFactory.create(
            db_session,
            uploaded_by=creator,
            filename="project_document.pdf",
            project=project,
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(member.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=project&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]

        # Should contain the project file
        filenames = [r["name"] for r in results]
        assert "project_document.pdf" in filenames


class TestSearchWithFiltersAndPagination:
    """Integration tests for search with filters and pagination"""

    def test_search_dynamic_pagination_limit(self, db_session: Session):
        """Test that search respects pagination limit"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create multiple files
        for i in range(15):
            FileFactory.create(
                db_session,
                uploaded_by=uploader,
                filename=f"document_{i}.pdf",
            )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=document&limit=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]
        assert len(results) <= 5

    def test_search_dynamic_pagination_page(self, db_session: Session):
        """Test that search pagination works across pages"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create multiple files
        for i in range(15):
            FileFactory.create(
                db_session,
                uploaded_by=uploader,
                filename=f"document_{i}.pdf",
            )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Get first page
        response1 = client.get("/api/v1/search/dynamic?search=document&limit=5&page=1")
        results1 = response1.json()["data"]

        # Act: Get second page
        response2 = client.get("/api/v1/search/dynamic?search=document&limit=5&page=2")
        results2 = response2.json()["data"]

        # Assert
        assert len(results1) > 0
        assert len(results2) > 0
        # Results should be different
        result_ids_1 = [r["id"] for r in results1]
        result_ids_2 = [r["id"] for r in results2]
        assert result_ids_1 != result_ids_2

    def test_search_dynamic_returns_pagination_metadata(self, db_session: Session):
        """Test that search returns pagination metadata"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create multiple files
        for i in range(25):
            FileFactory.create(
                db_session,
                uploaded_by=uploader,
                filename=f"document_{i}.pdf",
            )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=document&limit=10&page=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["limit"] == 10
        assert pagination["total"] >= 25

    def test_search_dynamic_empty_results(self, db_session: Session):
        """Test that search returns empty results for non-matching query"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create files with specific names
        FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="report.pdf",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=nonexistent&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        results = data["data"]
        assert len(results) == 0

    def test_search_dynamic_case_insensitive(self, db_session: Session):
        """Test that search is case-insensitive"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create file with mixed case name
        FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="QuarterlyReport.pdf",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Search with lowercase
        response = client.get("/api/v1/search/dynamic?search=quarterly&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]
        assert len(results) >= 1
        filenames = [r["name"] for r in results]
        assert "QuarterlyReport.pdf" in filenames

    def test_search_dynamic_partial_match(self, db_session: Session):
        """Test that search finds partial matches"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create files
        FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="comprehensive_analysis.pdf",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Search for partial term
        response = client.get("/api/v1/search/dynamic?search=analysis&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]
        assert len(results) >= 1
        filenames = [r["name"] for r in results]
        assert "comprehensive_analysis.pdf" in filenames

    def test_search_dynamic_sorts_by_relevance(self, db_session: Session):
        """Test that search results are sorted by relevance"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create files with different relevance
        FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="report.pdf",  # Exact match
        )
        FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="quarterly_report_summary.pdf",  # Contains "report"
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get("/api/v1/search/dynamic?search=report&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]
        assert len(results) >= 1
        # First result should be the exact match
        assert results[0]["name"] == "report.pdf"


class TestSearchIndexUpdatesAndDeletion:
    """Integration tests for search index updates and deletion"""

    def test_file_deletion_removes_from_search_results(self, db_session: Session):
        """Test that deleted files don't appear in search results"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create file
        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="temporary_document.pdf",
        )
        file_id = file.id
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 1: Search should find the file
        response1 = client.get("/api/v1/search/dynamic?search=temporary&limit=20")
        results1 = response1.json()["data"]
        assert len(results1) >= 1

        # Act 2: Delete the file
        delete_response = client.delete(f"/api/v1/files/{file_id}")
        assert delete_response.status_code == 200

        # Act 3: Search should not find the file
        response2 = client.get("/api/v1/search/dynamic?search=temporary&limit=20")
        results2 = response2.json()["data"]

        # Assert
        filenames = [r["name"] for r in results2]
        assert "temporary_document.pdf" not in filenames

    def test_project_deletion_removes_files_from_search(self, db_session: Session):
        """Test that files from deleted projects don't appear in search"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        # Create project and file
        project = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Temporary Project",
        )
        file = FileFactory.create(
            db_session,
            uploaded_by=creator,
            filename="project_file.pdf",
            project=project,
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 1: Search should find the file
        response1 = client.get("/api/v1/search/dynamic?search=project_file&limit=20")
        results1 = response1.json()["data"]
        assert len(results1) >= 1

        # Act 2: Delete the project (which should cascade delete files)
        from app.services.project import delete_project

        delete_project(db_session, project.id)
        db_session.commit()

        # Act 3: Search should not find the file
        response2 = client.get("/api/v1/search/dynamic?search=project_file&limit=20")
        results2 = response2.json()["data"]

        # Assert
        filenames = [r["name"] for r in results2]
        assert "project_file.pdf" not in filenames

    def test_file_metadata_update_reflects_in_search(self, db_session: Session):
        """Test that file metadata updates are reflected in search"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create file
        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="original_name.pdf",
        )
        file_id = file.id
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 1: Search for original name
        response1 = client.get("/api/v1/search/dynamic?search=original_name&limit=20")
        results1 = response1.json()["data"]
        assert len(results1) >= 1

        # Act 2: Update file name
        update_response = client.put(
            f"/api/v1/files/{file_id}",
            json={"filename": "updated_name.pdf"},
        )
        assert update_response.status_code == 200

        # Act 3: Search for new name
        response2 = client.get("/api/v1/search/dynamic?search=updated_name&limit=20")
        results2 = response2.json()["data"]

        # Assert
        assert len(results2) >= 1
        filenames = [r["name"] for r in results2]
        assert "updated_name.pdf" in filenames

    def test_search_consistency_across_multiple_queries(self, db_session: Session):
        """Test that search returns consistent results across multiple queries"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create files
        for i in range(5):
            FileFactory.create(
                db_session,
                uploaded_by=uploader,
                filename=f"consistent_file_{i}.pdf",
            )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Run same search multiple times
        response1 = client.get("/api/v1/search/dynamic?search=consistent&limit=20")
        results1 = response1.json()["data"]

        response2 = client.get("/api/v1/search/dynamic?search=consistent&limit=20")
        results2 = response2.json()["data"]

        response3 = client.get("/api/v1/search/dynamic?search=consistent&limit=20")
        results3 = response3.json()["data"]

        # Assert: Results should be identical
        assert len(results1) == len(results2) == len(results3)
        result_ids_1 = sorted([r["id"] for r in results1])
        result_ids_2 = sorted([r["id"] for r in results2])
        result_ids_3 = sorted([r["id"] for r in results3])
        assert result_ids_1 == result_ids_2 == result_ids_3

    def test_search_database_state_persistence(self, db_session: Session):
        """Test that search results reflect current database state"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Create initial file
        file1 = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="search_test_1.pdf",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 1: Search should find one file
        response1 = client.get("/api/v1/search/dynamic?search=search_test&limit=20")
        results1 = response1.json()["data"]
        assert len(results1) == 1

        # Act 2: Add another file
        file2 = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="search_test_2.pdf",
        )
        db_session.commit()

        # Act 3: Search should find two files
        response2 = client.get("/api/v1/search/dynamic?search=search_test&limit=20")
        results2 = response2.json()["data"]

        # Assert
        assert len(results2) == 2
        filenames = [r["name"] for r in results2]
        assert "search_test_1.pdf" in filenames
        assert "search_test_2.pdf" in filenames

    def test_search_with_project_filter_persists(self, db_session: Session):
        """Test that project filter is applied correctly and persists"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        # Create two projects
        project1 = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Project A",
        )
        project2 = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Project B",
        )

        # Create files in each project
        file1 = FileFactory.create(
            db_session,
            uploaded_by=creator,
            filename="document.pdf",
            project=project1,
        )
        file2 = FileFactory.create(
            db_session,
            uploaded_by=creator,
            filename="document.pdf",
            project=project2,
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Search with project filter
        response = client.get(f"/api/v1/search/dynamic?search=document&project_id={project1.id}&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]

        # Should only return files from project1
        for result in results:
            if result["type"] == "file":
                # Verify it's from the correct project
                assert result["id"] == str(file1.id)

    def test_search_with_meeting_filter_persists(self, db_session: Session):
        """Test that meeting filter is applied correctly and persists"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        # Create two meetings
        meeting1 = MeetingFactory.create(
            db_session,
            created_by=creator,
            title="Meeting A",
        )
        meeting2 = MeetingFactory.create(
            db_session,
            created_by=creator,
            title="Meeting B",
        )

        # Create files in each meeting
        file1 = FileFactory.create(
            db_session,
            uploaded_by=creator,
            filename="notes.pdf",
            meeting=meeting1,
        )
        file2 = FileFactory.create(
            db_session,
            uploaded_by=creator,
            filename="notes.pdf",
            meeting=meeting2,
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Search with meeting filter
        response = client.get(f"/api/v1/search/dynamic?search=notes&meeting_id={meeting1.id}&limit=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        results = data["data"]

        # Should only return files from meeting1
        for result in results:
            if result["type"] == "file":
                # Verify it's from the correct meeting
                assert result["id"] == str(file1.id)
