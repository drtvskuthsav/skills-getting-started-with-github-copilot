"""
Tests for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


def test_root_redirect(client):
    """Test that root redirects to static/index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client):
    """Test retrieving all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, dict)
    assert "Chess Club" in data
    assert "Programming Class" in data
    
    # Verify structure of an activity
    chess_club = data["Chess Club"]
    assert "description" in chess_club
    assert "schedule" in chess_club
    assert "max_participants" in chess_club
    assert "participants" in chess_club
    assert isinstance(chess_club["participants"], list)


def test_signup_for_activity_success(client):
    """Test successfully signing up for an activity"""
    response = client.post(
        "/activities/Chess%20Club/signup?email=test@mergington.edu"
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "test@mergington.edu" in data["message"]
    assert "Chess Club" in data["message"]
    
    # Verify participant was added
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert "test@mergington.edu" in activities_data["Chess Club"]["participants"]


def test_signup_for_nonexistent_activity(client):
    """Test signing up for an activity that doesn't exist"""
    response = client.post(
        "/activities/Fake%20Activity/signup?email=test@mergington.edu"
    )
    assert response.status_code == 404
    
    data = response.json()
    assert "detail" in data
    assert "Activity not found" in data["detail"]


def test_signup_duplicate_participant(client):
    """Test signing up when already registered"""
    # First signup should succeed
    response1 = client.post(
        "/activities/Chess%20Club/signup?email=new@mergington.edu"
    )
    assert response1.status_code == 200
    
    # Second signup should fail
    response2 = client.post(
        "/activities/Chess%20Club/signup?email=new@mergington.edu"
    )
    assert response2.status_code == 400
    
    data = response2.json()
    assert "detail" in data
    assert "already signed up" in data["detail"]


def test_unregister_from_activity_success(client):
    """Test successfully unregistering from an activity"""
    # First, sign up
    client.post("/activities/Chess%20Club/signup?email=remove@mergington.edu")
    
    # Then unregister
    response = client.delete(
        "/activities/Chess%20Club/unregister?email=remove@mergington.edu"
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "remove@mergington.edu" in data["message"]
    assert "Chess Club" in data["message"]
    
    # Verify participant was removed
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert "remove@mergington.edu" not in activities_data["Chess Club"]["participants"]


def test_unregister_from_nonexistent_activity(client):
    """Test unregistering from an activity that doesn't exist"""
    response = client.delete(
        "/activities/Fake%20Activity/unregister?email=test@mergington.edu"
    )
    assert response.status_code == 404
    
    data = response.json()
    assert "detail" in data
    assert "Activity not found" in data["detail"]


def test_unregister_not_signed_up(client):
    """Test unregistering when not signed up"""
    response = client.delete(
        "/activities/Chess%20Club/unregister?email=notsignedup@mergington.edu"
    )
    assert response.status_code == 400
    
    data = response.json()
    assert "detail" in data
    assert "not signed up" in data["detail"]


def test_unregister_existing_participant(client):
    """Test unregistering an existing participant"""
    # Use a participant that already exists in the initial data
    response = client.delete(
        "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
    )
    assert response.status_code == 200
    
    # Verify participant was removed
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]


def test_multiple_signups_different_activities(client):
    """Test signing up for multiple different activities"""
    email = "multi@mergington.edu"
    
    # Sign up for Chess Club
    response1 = client.post(f"/activities/Chess%20Club/signup?email={email}")
    assert response1.status_code == 200
    
    # Sign up for Programming Class
    response2 = client.post(f"/activities/Programming%20Class/signup?email={email}")
    assert response2.status_code == 200
    
    # Verify participant is in both activities
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email in activities_data["Chess Club"]["participants"]
    assert email in activities_data["Programming Class"]["participants"]


def test_activity_capacity_tracking(client):
    """Test that participant count affects availability"""
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    
    chess_club = activities_data["Chess Club"]
    initial_count = len(chess_club["participants"])
    max_participants = chess_club["max_participants"]
    
    assert initial_count <= max_participants
    assert max_participants == 12  # Verify expected capacity
