"""Unit tests for meeting agent date parser"""

from datetime import datetime, timedelta, timezone

from faker import Faker

from app.utils.meeting_agent.date_parser import (
    get_end_of_month,
    get_end_of_week,
    get_next_day_of_week,
    parse_due_date_to_datetime,
)

fake = Faker()


class TestGetNextDayOfWeek:
    """Tests for get_next_day_of_week function"""

    def test_get_next_day_of_week_monday(self):
        """Test getting next Monday"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)  # Wednesday
        result = get_next_day_of_week("Monday", base_date)

        assert result > base_date
        assert result.weekday() == 0  # Monday

    def test_get_next_day_of_week_friday(self):
        """Test getting next Friday"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)  # Wednesday
        result = get_next_day_of_week("Friday", base_date)

        assert result > base_date
        assert result.weekday() == 4  # Friday

    def test_get_next_day_of_week_sunday(self):
        """Test getting next Sunday"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)  # Wednesday
        result = get_next_day_of_week("Sunday", base_date)

        assert result > base_date
        assert result.weekday() == 6  # Sunday

    def test_get_next_day_of_week_case_insensitive(self):
        """Test day name is case insensitive"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result1 = get_next_day_of_week("monday", base_date)
        result2 = get_next_day_of_week("MONDAY", base_date)
        result3 = get_next_day_of_week("Monday", base_date)

        assert result1 == result2 == result3

    def test_get_next_day_of_week_invalid_day(self):
        """Test invalid day name returns base date"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = get_next_day_of_week("InvalidDay", base_date)

        assert result == base_date

    def test_get_next_day_of_week_all_weekdays(self):
        """Test all weekdays"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for i, day in enumerate(weekdays):
            result = get_next_day_of_week(day, base_date)
            assert result.weekday() == i

    def test_get_next_day_of_week_no_base_date(self):
        """Test function uses current date when base_date is None"""
        result = get_next_day_of_week("Monday")

        assert result is not None
        assert result.weekday() == 0


class TestGetEndOfMonth:
    """Tests for get_end_of_month function"""

    def test_get_end_of_month_january(self):
        """Test end of January"""
        base_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        result = get_end_of_month(base_date)

        assert result.month == 1
        assert result.day == 31

    def test_get_end_of_month_february(self):
        """Test end of February (non-leap year)"""
        base_date = datetime(2025, 2, 10, tzinfo=timezone.utc)
        result = get_end_of_month(base_date)

        assert result.month == 2
        assert result.day == 28

    def test_get_end_of_month_february_leap_year(self):
        """Test end of February in leap year"""
        base_date = datetime(2024, 2, 10, tzinfo=timezone.utc)
        result = get_end_of_month(base_date)

        assert result.month == 2
        assert result.day == 29

    def test_get_end_of_month_december(self):
        """Test end of December"""
        base_date = datetime(2025, 12, 15, tzinfo=timezone.utc)
        result = get_end_of_month(base_date)

        assert result.month == 12
        assert result.day == 31

    def test_get_end_of_month_no_base_date(self):
        """Test function uses current month when base_date is None"""
        result = get_end_of_month()

        assert result is not None
        assert result.month in range(1, 13)


class TestGetEndOfWeek:
    """Tests for get_end_of_week function"""

    def test_get_end_of_week_wednesday(self):
        """Test end of week from Wednesday"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)  # Wednesday
        result = get_end_of_week(base_date)

        assert result.weekday() == 6  # Sunday
        assert result > base_date

    def test_get_end_of_week_monday(self):
        """Test end of week from Monday"""
        base_date = datetime(2024, 12, 30, tzinfo=timezone.utc)  # Monday
        result = get_end_of_week(base_date)

        assert result.weekday() == 6  # Sunday
        assert result > base_date

    def test_get_end_of_week_sunday(self):
        """Test end of week from Sunday"""
        base_date = datetime(2024, 12, 29, tzinfo=timezone.utc)  # Sunday
        result = get_end_of_week(base_date)

        assert result.weekday() == 6  # Sunday
        # Should be next Sunday

    def test_get_end_of_week_friday(self):
        """Test end of week from Friday"""
        base_date = datetime(2024, 12, 27, tzinfo=timezone.utc)  # Friday
        result = get_end_of_week(base_date)

        assert result.weekday() == 6  # Sunday
        assert result > base_date

    def test_get_end_of_week_no_base_date(self):
        """Test function uses current week when base_date is None"""
        result = get_end_of_week()

        assert result is not None
        assert result.weekday() == 6


class TestParseDueDateToDatetime:
    """Tests for parse_due_date_to_datetime function"""

    def test_parse_days_duration(self):
        """Test parsing 'X days' format"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = parse_due_date_to_datetime("3 days", base_date)

        assert result is not None
        expected_date = base_date + timedelta(days=3)
        assert result == expected_date

    def test_parse_weeks_duration(self):
        """Test parsing 'X weeks' format"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = parse_due_date_to_datetime("2 weeks", base_date)

        assert result is not None
        expected_date = base_date + timedelta(weeks=2)
        assert result == expected_date

    def test_parse_end_of_week(self):
        """Test parsing 'end of week'"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)  # Wednesday
        result = parse_due_date_to_datetime("end of week", base_date)

        assert result is not None
        assert result.weekday() == 6  # Sunday

    def test_parse_end_of_month(self):
        """Test parsing 'end of month'"""
        base_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        result = parse_due_date_to_datetime("end of month", base_date)

        assert result is not None
        assert result.month == 1
        assert result.day == 31

    def test_parse_end_of_this_month(self):
        """Test parsing 'end of this month'"""
        base_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        result = parse_due_date_to_datetime("end of this month", base_date)

        assert result is not None
        assert result.month == 1

    def test_parse_next_day(self):
        """Test parsing 'next Monday' format"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)  # Wednesday
        result = parse_due_date_to_datetime("next Monday", base_date)

        assert result is not None
        assert result.weekday() == 0  # Monday

    def test_parse_next_friday(self):
        """Test parsing 'next Friday' format"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)  # Wednesday
        result = parse_due_date_to_datetime("next Friday", base_date)

        assert result is not None
        assert result.weekday() == 4  # Friday

    def test_parse_none_string(self):
        """Test parsing 'null' string returns None"""
        result = parse_due_date_to_datetime("null")

        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None"""
        result = parse_due_date_to_datetime("")

        assert result is None

    def test_parse_none_value(self):
        """Test parsing None returns None"""
        result = parse_due_date_to_datetime(None)

        assert result is None

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only string returns None"""
        result = parse_due_date_to_datetime("   ")

        assert result is None

    def test_parse_invalid_format(self):
        """Test parsing invalid format returns None"""
        result = parse_due_date_to_datetime("invalid format text")

        assert result is None

    def test_parse_case_insensitive(self):
        """Test parsing is case insensitive"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result1 = parse_due_date_to_datetime("3 days", base_date)
        result2 = parse_due_date_to_datetime("3 DAYS", base_date)
        result3 = parse_due_date_to_datetime("3 Days", base_date)

        assert result1 == result2 == result3

    def test_parse_with_whitespace(self):
        """Test parsing strings with extra whitespace"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = parse_due_date_to_datetime("  3 days  ", base_date)

        assert result is not None
        expected_date = base_date + timedelta(days=3)
        assert result == expected_date

    def test_parse_one_day(self):
        """Test parsing '1 day'"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = parse_due_date_to_datetime("1 day", base_date)

        assert result is not None
        assert result == base_date + timedelta(days=1)

    def test_parse_one_week(self):
        """Test parsing '1 week'"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = parse_due_date_to_datetime("1 week", base_date)

        assert result is not None
        assert result == base_date + timedelta(weeks=1)

    def test_parse_large_number_days(self):
        """Test parsing large number of days"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = parse_due_date_to_datetime("365 days", base_date)

        assert result is not None
        assert result == base_date + timedelta(days=365)
