from _typeshed import Incomplete
from stravalib import exc as exc, model as model, unithelper as unithelper
from stravalib.exc import warn_param_deprecation as warn_param_deprecation, warn_param_unofficial as warn_param_unofficial
from stravalib.protocol import ApiV3 as ApiV3
from stravalib.unithelper import is_quantity_type as is_quantity_type
from stravalib.util import limiter as limiter

class Client:
    log: Incomplete
    protocol: Incomplete
    def __init__(self, access_token: Incomplete | None = ..., rate_limit_requests: bool = ..., rate_limiter: Incomplete | None = ..., requests_session: Incomplete | None = ...) -> None: ...
    @property
    def access_token(self): ...
    @access_token.setter
    def access_token(self, v) -> None: ...
    def authorization_url(self, client_id, redirect_uri, approval_prompt: str = ..., scope: Incomplete | None = ..., state: Incomplete | None = ...): ...
    def exchange_code_for_token(self, client_id, client_secret, code): ...
    def refresh_access_token(self, client_id, client_secret, refresh_token): ...
    def deauthorize(self) -> None: ...
    def get_activities(self, before: Incomplete | None = ..., after: Incomplete | None = ..., limit: Incomplete | None = ...): ...
    def get_athlete(self): ...
    def get_athlete_friends(self, athlete_id: Incomplete | None = ..., limit: Incomplete | None = ...): ...
    def update_athlete(self, city: Incomplete | None = ..., state: Incomplete | None = ..., country: Incomplete | None = ..., sex: Incomplete | None = ..., weight: Incomplete | None = ...): ...
    def get_athlete_followers(self, athlete_id: Incomplete | None = ..., limit: Incomplete | None = ...): ...
    def get_both_following(self, athlete_id, limit: Incomplete | None = ...) -> None: ...
    def get_athlete_koms(self, athlete_id, limit: Incomplete | None = ...): ...
    def get_athlete_stats(self, athlete_id: Incomplete | None = ...): ...
    def get_athlete_clubs(self): ...
    def join_club(self, club_id) -> None: ...
    def leave_club(self, club_id) -> None: ...
    def get_club(self, club_id): ...
    def get_club_members(self, club_id, limit: Incomplete | None = ...): ...
    def get_club_activities(self, club_id, limit: Incomplete | None = ...): ...
    def get_activity(self, activity_id, include_all_efforts: bool = ...): ...
    def get_friend_activities(self, limit: Incomplete | None = ...) -> None: ...
    def create_activity(self, name, activity_type, start_date_local, elapsed_time, description: Incomplete | None = ..., distance: Incomplete | None = ...): ...
    def update_activity(self, activity_id, name: Incomplete | None = ..., activity_type: Incomplete | None = ..., private: Incomplete | None = ..., commute: Incomplete | None = ..., trainer: Incomplete | None = ..., gear_id: Incomplete | None = ..., description: Incomplete | None = ..., device_name: Incomplete | None = ..., hide_from_home: Incomplete | None = ...): ...
    def upload_activity(self, activity_file, data_type, name: Incomplete | None = ..., description: Incomplete | None = ..., activity_type: Incomplete | None = ..., private: Incomplete | None = ..., external_id: Incomplete | None = ..., trainer: Incomplete | None = ..., commute: Incomplete | None = ...): ...
    def delete_activity(self, activity_id) -> None: ...
    def get_activity_zones(self, activity_id): ...
    def get_activity_comments(self, activity_id, markdown: bool = ..., limit: Incomplete | None = ...): ...
    def get_activity_kudos(self, activity_id, limit: Incomplete | None = ...): ...
    def get_activity_photos(self, activity_id, size: Incomplete | None = ..., only_instagram: bool = ...): ...
    def get_activity_laps(self, activity_id): ...
    def get_related_activities(self, activity_id, limit: Incomplete | None = ...) -> None: ...
    def get_gear(self, gear_id): ...
    def get_segment_effort(self, effort_id): ...
    def get_segment(self, segment_id): ...
    def get_starred_segments(self, limit: Incomplete | None = ...): ...
    def get_athlete_starred_segments(self, athlete_id, limit: Incomplete | None = ...): ...
    def get_segment_leaderboard(self, segment_id, gender: Incomplete | None = ..., age_group: Incomplete | None = ..., weight_class: Incomplete | None = ..., following: Incomplete | None = ..., club_id: Incomplete | None = ..., timeframe: Incomplete | None = ..., top_results_limit: Incomplete | None = ..., page: Incomplete | None = ..., context_entries: Incomplete | None = ...): ...
    def get_segment_efforts(self, segment_id, athlete_id: Incomplete | None = ..., start_date_local: Incomplete | None = ..., end_date_local: Incomplete | None = ..., limit: Incomplete | None = ...): ...
    def explore_segments(self, bounds, activity_type: Incomplete | None = ..., min_cat: Incomplete | None = ..., max_cat: Incomplete | None = ...): ...
    def get_activity_streams(self, activity_id, types: Incomplete | None = ..., resolution: Incomplete | None = ..., series_type: Incomplete | None = ...): ...
    def get_effort_streams(self, effort_id, types: Incomplete | None = ..., resolution: Incomplete | None = ..., series_type: Incomplete | None = ...): ...
    def get_segment_streams(self, segment_id, types: Incomplete | None = ..., resolution: Incomplete | None = ..., series_type: Incomplete | None = ...): ...
    def get_routes(self, athlete_id: Incomplete | None = ..., limit: Incomplete | None = ...): ...
    def get_route(self, route_id): ...
    def get_route_streams(self, route_id): ...
    def create_subscription(self, client_id, client_secret, callback_url, verify_token=...): ...
    def handle_subscription_callback(self, raw, verify_token=...): ...
    def handle_subscription_update(self, raw): ...
    def list_subscriptions(self, client_id, client_secret): ...
    def delete_subscription(self, subscription_id, client_id, client_secret) -> None: ...

class BatchedResultsIterator:
    default_per_page: int
    log: Incomplete
    entity: Incomplete
    bind_client: Incomplete
    result_fetcher: Incomplete
    limit: Incomplete
    per_page: Incomplete
    def __init__(self, entity, result_fetcher, bind_client: Incomplete | None = ..., limit: Incomplete | None = ..., per_page: Incomplete | None = ...) -> None: ...
    def reset(self) -> None: ...
    def __iter__(self): ...
    def __next__(self): ...
    def next(self): ...

class ActivityUploader:
    client: Incomplete
    response: Incomplete
    def __init__(self, client, response, raise_exc: bool = ...) -> None: ...
    upload_id: Incomplete
    external_id: Incomplete
    activity_id: Incomplete
    status: Incomplete
    error: Incomplete
    def update_from_response(self, response, raise_exc: bool = ...) -> None: ...
    @property
    def is_processing(self): ...
    @property
    def is_error(self): ...
    @property
    def is_complete(self): ...
    def raise_for_error(self) -> None: ...
    def poll(self) -> None: ...
    def wait(self, timeout: Incomplete | None = ..., poll_interval: float = ...): ...
