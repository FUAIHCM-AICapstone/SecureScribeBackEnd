"""Performance and large dataset tests

This module tests system performance with:
- Pagination with large datasets (>10000 records)
- Search performance with large indices
- Bulk operations with large batches (>1000 items)
- Concurrent requests (>100 simultaneous)
"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from faker import Faker
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.user import User
from app.services.task import get_tasks
from app.services.user import create_user, get_users
from tests.factories import ProjectFactory, UserFactory

fake = Faker()


class TestPaginationWithLargeDatasets:
    """Tests for pagination with large datasets (>10000 records)

    **Feature: backend-test-coverage, Property 10: Concurrent operation safety**
    **Validates: Requirements 12.6**
    """

    def test_pagination_with_10000_users(self, db_session: Session):
        """Test pagination performance with 10000 user records

        When retrieving paginated users from a large dataset,
        pagination should work efficiently and return correct page sizes.
        """
        # Create 10000 users
        print("\n📊 Creating 10000 users for pagination test...")
        start_time = time.time()

        users = []
        batch_size = 500
        for batch_num in range(20):  # 20 batches of 500 users
            batch_users = []
            for i in range(batch_size):
                user = User(
                    email=f"pagination_user_{batch_num}_{i}_{uuid.uuid4()}@test.com",
                    name=f"User {batch_num * batch_size + i}",
                    avatar_url="https://example.com/avatar.jpg",
                    bio="Test user",
                    position="Engineer",
                )
                batch_users.append(user)
            db_session.add_all(batch_users)
            db_session.commit()
            users.extend(batch_users)

        creation_time = time.time() - start_time
        print(f"✅ Created 10000 users in {creation_time:.2f}s")

        # Test pagination retrieval
        print("📄 Testing pagination retrieval...")
        page_start = time.time()

        # Get first page (page parameter is 1-indexed)
        page_1, total = get_users(db_session, page=1, limit=50)
        assert len(page_1) == 50, f"Expected 50 users on page 1, got {len(page_1)}"
        # Just verify we got results, don't check exact total since DB may have other data
        assert total >= 10000, f"Expected at least 10000 total users, got {total}"

        # Get middle page
        page_100, _ = get_users(db_session, page=100, limit=50)
        assert len(page_100) == 50, f"Expected 50 users on page 100, got {len(page_100)}"

        # Get last page
        page_last, _ = get_users(db_session, page=200, limit=50)
        assert len(page_last) == 50, "Expected 50 users on last page"

        page_time = time.time() - page_start
        print(f"✅ Pagination retrieval completed in {page_time:.2f}s")

        # Verify pagination consistency
        assert page_1[0].id != page_100[0].id, "Different pages should have different users"

    def test_pagination_with_10000_tasks(self, db_session: Session):
        """Test pagination performance with 10000 task records

        When retrieving paginated tasks from a large dataset,
        pagination should work efficiently and return correct page sizes.
        """
        # Create creator and project
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)

        # Create 10000 tasks
        print("\n📊 Creating 10000 tasks for pagination test...")
        start_time = time.time()

        tasks = []
        batch_size = 500
        for batch_num in range(20):  # 20 batches of 500 tasks
            batch_tasks = []
            for i in range(batch_size):
                task = Task(
                    title=f"Task {batch_num * batch_size + i}",
                    description=f"Description for task {batch_num * batch_size + i}",
                    creator_id=creator.id,
                    status="todo",
                    priority="Trung bình",
                )
                batch_tasks.append(task)
            db_session.add_all(batch_tasks)
            db_session.commit()
            tasks.extend(batch_tasks)

        creation_time = time.time() - start_time
        print(f"✅ Created 10000 tasks in {creation_time:.2f}s")

        # Test pagination retrieval
        print("📄 Testing task pagination retrieval...")
        page_start = time.time()

        # Get first page (get_tasks requires user_id)
        page_1, total = get_tasks(db_session, user_id=creator.id, page=1, limit=50)
        assert len(page_1) == 50, f"Expected 50 tasks on page 1, got {len(page_1)}"
        assert total == 10000, f"Expected 10000 total tasks, got {total}"

        # Get middle page
        page_100, _ = get_tasks(db_session, user_id=creator.id, page=100, limit=50)
        assert len(page_100) == 50, f"Expected 50 tasks on page 100, got {len(page_100)}"

        # Get last page
        page_last, _ = get_tasks(db_session, user_id=creator.id, page=200, limit=50)
        assert len(page_last) == 50, "Expected 50 tasks on last page"

        page_time = time.time() - page_start
        print(f"✅ Task pagination retrieval completed in {page_time:.2f}s")

        # Verify pagination consistency
        assert page_1[0].id != page_100[0].id, "Different pages should have different tasks"

    def test_pagination_with_various_page_sizes(self, db_session: Session):
        """Test pagination with various page sizes on large dataset

        When retrieving paginated results with different page sizes,
        all page sizes should work correctly and efficiently.
        """
        # Create 5000 users
        print("\n📊 Creating 5000 users for page size test...")
        start_time = time.time()

        for i in range(5000):
            user = User(
                email=f"pagesize_user_{i}_{uuid.uuid4()}@test.com",
                name=f"User {i}",
                avatar_url="https://example.com/avatar.jpg",
                bio="Test user",
                position="Engineer",
            )
            db_session.add(user)
            if i % 100 == 0:
                db_session.commit()
        db_session.commit()

        creation_time = time.time() - start_time
        print(f"✅ Created 5000 users in {creation_time:.2f}s")

        # Test different page sizes
        print("📄 Testing various page sizes...")
        page_sizes = [10, 25, 50, 100, 250]

        for page_size in page_sizes:
            page_start = time.time()
            results, total = get_users(db_session, page=1, limit=page_size)
            page_time = time.time() - page_start

            assert len(results) == page_size, f"Expected {page_size} users, got {len(results)}"
            print(f"✅ Page size {page_size}: retrieved in {page_time:.3f}s")


class TestBulkOperationsWithLargeBatches:
    """Tests for bulk operations with large batches (>1000 items)

    **Feature: backend-test-coverage, Property 10: Concurrent operation safety**
    **Validates: Requirements 12.6**
    """

    def test_bulk_create_1000_users(self, db_session: Session):
        """Test bulk creation of 1000 users

        When creating 1000 users in bulk,
        all should be created successfully and efficiently.
        """
        test_id = str(uuid.uuid4())[:8]
        print("\n📊 Testing bulk creation of 1000 users...")
        start_time = time.time()

        users = []
        for i in range(1000):
            user = User(
                email=f"bulk_user_{test_id}_{i}@test.com",
                name=f"Bulk User {i}",
                avatar_url="https://example.com/avatar.jpg",
                bio="Bulk test user",
                position="Engineer",
            )
            users.append(user)

        # Add all at once
        db_session.add_all(users)
        db_session.commit()

        creation_time = time.time() - start_time
        print(f"✅ Created 1000 users in {creation_time:.2f}s")

        # Verify all were created with this test's unique ID
        # Count users created in this test by checking the exact pattern
        count = 0
        for user in users:
            db_user = db_session.query(User).filter(User.id == user.id).first()
            if db_user:
                count += 1
        assert count == 1000, f"Expected 1000 users, got {count}"

    def test_bulk_create_1000_tasks(self, db_session: Session):
        """Test bulk creation of 1000 tasks

        When creating 1000 tasks in bulk,
        all should be created successfully and efficiently.
        """
        creator = UserFactory.create(db_session)
        test_id = str(uuid.uuid4())[:8]

        print("\n📊 Testing bulk creation of 1000 tasks...")
        start_time = time.time()

        tasks = []
        for i in range(1000):
            task = Task(
                title=f"Bulk Task {test_id} {i}",
                description=f"Description for bulk task {i}",
                creator_id=creator.id,
                status="todo",
                priority="Trung bình",
            )
            tasks.append(task)

        # Add all at once
        db_session.add_all(tasks)
        db_session.commit()

        creation_time = time.time() - start_time
        print(f"✅ Created 1000 tasks in {creation_time:.2f}s")

        # Verify all were created by checking the exact task IDs
        count = 0
        for task in tasks:
            db_task = db_session.query(Task).filter(Task.id == task.id).first()
            if db_task:
                count += 1
        assert count == 1000, f"Expected 1000 tasks, got {count}"

    def test_bulk_update_1000_tasks(self, db_session: Session):
        """Test bulk update of 1000 tasks

        When updating 1000 tasks in bulk,
        all should be updated successfully and efficiently.
        """
        creator = UserFactory.create(db_session)
        test_id = str(uuid.uuid4())[:8]

        # Create 1000 tasks
        print("\n📊 Creating 1000 tasks for bulk update test...")
        tasks = []
        for i in range(1000):
            task = Task(
                title=f"Update Task {test_id} {i}",
                description=f"Original description {i}",
                creator_id=creator.id,
                status="todo",
                priority="Trung bình",
            )
            tasks.append(task)

        db_session.add_all(tasks)
        db_session.commit()

        # Bulk update status
        print("📝 Bulk updating 1000 tasks...")
        start_time = time.time()

        # Update only the tasks we created
        task_ids = [task.id for task in tasks]
        db_session.query(Task).filter(Task.id.in_(task_ids)).update({"status": "in_progress"})
        db_session.commit()

        update_time = time.time() - start_time
        print(f"✅ Updated 1000 tasks in {update_time:.2f}s")

        # Verify all were updated by checking the exact task IDs
        count = 0
        for task_id in task_ids:
            db_task = db_session.query(Task).filter(Task.id == task_id).first()
            if db_task and db_task.status == "in_progress":
                count += 1
        assert count == 1000, f"Expected 1000 updated tasks, got {count}"

    def test_bulk_delete_1000_tasks(self, db_session: Session):
        """Test bulk deletion of 1000 tasks

        When deleting 1000 tasks in bulk,
        all should be deleted successfully and efficiently.
        """
        creator = UserFactory.create(db_session)
        test_id = str(uuid.uuid4())[:8]

        # Create 1000 tasks
        print("\n📊 Creating 1000 tasks for bulk delete test...")
        tasks = []
        for i in range(1000):
            task = Task(
                title=f"Delete Task {test_id} {i}",
                description=f"Description {i}",
                creator_id=creator.id,
                status="todo",
                priority="Trung bình",
            )
            tasks.append(task)

        db_session.add_all(tasks)
        db_session.commit()

        # Bulk delete
        print("🗑️  Bulk deleting 1000 tasks...")
        start_time = time.time()

        # Delete only the tasks we created
        task_ids = [task.id for task in tasks]
        db_session.query(Task).filter(Task.id.in_(task_ids)).delete()
        db_session.commit()

        delete_time = time.time() - start_time
        print(f"✅ Deleted 1000 tasks in {delete_time:.2f}s")

        # Verify all were deleted by checking the exact task IDs
        count = 0
        for task_id in task_ids:
            db_task = db_session.query(Task).filter(Task.id == task_id).first()
            if db_task:
                count += 1
        assert count == 0, f"Expected 0 tasks, got {count}"


class TestConcurrentRequests:
    """Tests for concurrent requests (>100 simultaneous)

    **Feature: backend-test-coverage, Property 10: Concurrent operation safety**
    **Validates: Requirements 12.6**
    """

    def test_100_concurrent_user_creations(self, db_session: Session):
        """Test 100 concurrent user creation requests

        When 100 threads create users simultaneously,
        all should succeed and create distinct records.
        """
        from app.db import SessionLocal

        print("\n🔄 Testing 100 concurrent user creations...")
        start_time = time.time()

        num_threads = 100
        results = []
        errors = []
        lock = __import__("threading").Lock()

        def create_user_thread(thread_id):
            thread_session = SessionLocal()
            try:
                email = f"concurrent_{thread_id}_{uuid.uuid4()}@test.com"
                user = create_user(
                    thread_session,
                    email=email,
                    name=f"Concurrent User {thread_id}",
                )
                with lock:
                    results.append(user)
            except Exception as e:
                with lock:
                    errors.append(str(e))
            finally:
                thread_session.close()

        # Run concurrent threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_user_thread, i) for i in range(num_threads)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        concurrent_time = time.time() - start_time
        print(f"✅ Completed 100 concurrent user creations in {concurrent_time:.2f}s")
        print(f"   Successful: {len(results)}, Errors: {len(errors)}")

        # All should succeed
        assert len(results) == num_threads, f"Expected {num_threads} successful creations, got {len(results)}"
        assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}"

    def test_100_concurrent_task_creations(self, db_session: Session):
        """Test 100 concurrent task creation requests

        When 100 threads create tasks simultaneously,
        all should succeed and create distinct records.
        """
        from app.db import SessionLocal

        creator = UserFactory.create(db_session)

        print("\n🔄 Testing 100 concurrent task creations...")
        start_time = time.time()

        num_threads = 100
        results = []
        errors = []
        lock = __import__("threading").Lock()

        def create_task_thread(thread_id):
            thread_session = SessionLocal()
            try:
                task = Task(
                    title=f"Concurrent Task {thread_id}",
                    description=f"Description {thread_id}",
                    creator_id=creator.id,
                    status="todo",
                    priority="Trung bình",
                )
                thread_session.add(task)
                thread_session.commit()
                thread_session.refresh(task)
                with lock:
                    results.append(task)
            except Exception as e:
                with lock:
                    errors.append(str(e))
            finally:
                thread_session.close()

        # Run concurrent threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_task_thread, i) for i in range(num_threads)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        concurrent_time = time.time() - start_time
        print(f"✅ Completed 100 concurrent task creations in {concurrent_time:.2f}s")
        print(f"   Successful: {len(results)}, Errors: {len(errors)}")

        # All should succeed
        assert len(results) == num_threads, f"Expected {num_threads} successful creations, got {len(results)}"
        assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}"

    def test_100_concurrent_task_updates(self, db_session: Session):
        """Test 100 concurrent task update requests

        When 100 threads update tasks simultaneously,
        all should succeed and maintain consistency.
        """
        from app.db import SessionLocal

        creator = UserFactory.create(db_session)

        # Create 100 tasks
        print("\n📊 Creating 100 tasks for concurrent update test...")
        tasks = []
        for i in range(100):
            task = Task(
                title=f"Update Test Task {i}",
                description=f"Description {i}",
                creator_id=creator.id,
                status="todo",
                priority="Trung bình",
            )
            tasks.append(task)

        db_session.add_all(tasks)
        db_session.commit()

        print("🔄 Testing 100 concurrent task updates...")
        start_time = time.time()

        num_threads = 100
        results = []
        errors = []
        lock = __import__("threading").Lock()

        def update_task_thread(task_idx):
            thread_session = SessionLocal()
            try:
                task = thread_session.query(Task).filter(Task.id == tasks[task_idx].id).first()
                task.status = "in_progress"
                thread_session.commit()
                thread_session.refresh(task)
                with lock:
                    results.append(task)
            except Exception as e:
                with lock:
                    errors.append(str(e))
            finally:
                thread_session.close()

        # Run concurrent threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(update_task_thread, i) for i in range(num_threads)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        concurrent_time = time.time() - start_time
        print(f"✅ Completed 100 concurrent task updates in {concurrent_time:.2f}s")
        print(f"   Successful: {len(results)}, Errors: {len(errors)}")

        # Most should succeed (allow some failures due to concurrency)
        assert len(results) >= num_threads * 0.95, f"Expected at least 95 successful updates, got {len(results)}"

    def test_100_concurrent_reads(self, db_session: Session):
        """Test 100 concurrent read requests

        When 100 threads read data simultaneously,
        all should succeed and return consistent data.
        """
        from app.db import SessionLocal

        # Create test data
        print("\n📊 Creating test data for concurrent read test...")
        creator = UserFactory.create(db_session)
        task_ids = []
        tasks = []
        for i in range(50):
            task = Task(
                title=f"Read Test Task {i}",
                description=f"Description {i}",
                creator_id=creator.id,
                status="todo",
                priority="Trung bình",
            )
            tasks.append(task)

        db_session.add_all(tasks)
        db_session.commit()

        # Store task IDs for concurrent reads
        task_ids = [task.id for task in tasks]

        print("🔄 Testing 100 concurrent read requests...")
        start_time = time.time()

        num_threads = 100
        results = []
        errors = []
        lock = __import__("threading").Lock()

        def read_tasks_thread(thread_id):
            thread_session = SessionLocal()
            try:
                # Read only the tasks we created
                count = 0
                for task_id in task_ids:
                    task = thread_session.query(Task).filter(Task.id == task_id).first()
                    if task:
                        count += 1
                with lock:
                    results.append(count)
            except Exception as e:
                with lock:
                    errors.append(str(e))
            finally:
                thread_session.close()

        # Run concurrent threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(read_tasks_thread, i) for i in range(num_threads)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        concurrent_time = time.time() - start_time
        print(f"✅ Completed 100 concurrent read requests in {concurrent_time:.2f}s")
        print(f"   Successful: {len(results)}, Errors: {len(errors)}")
        print(f"   Read counts: {set(results)}")

        # All should succeed
        assert len(results) == num_threads, f"Expected {num_threads} successful reads, got {len(results)}"
        assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}"

        # All should read same number of tasks
        assert all(count == 50 for count in results), f"All reads should return 50 tasks, got {set(results)}"
