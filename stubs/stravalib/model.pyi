from collections.abc import Sequence
from stravalib import exc as exc
from stravalib.attributes import Attribute as Attribute, ChoicesAttribute as ChoicesAttribute, DETAILED as DETAILED, DateAttribute as DateAttribute, EntityAttribute as EntityAttribute, EntityCollection as EntityCollection, LocationAttribute as LocationAttribute, META as META, SUMMARY as SUMMARY, TimeIntervalAttribute as TimeIntervalAttribute, TimestampAttribute as TimestampAttribute, TimezoneAttribute as TimezoneAttribute
from typing import Any

class BaseEntity:
    log: Any
    def __init__(self, **kwargs) -> None: ...
    def to_dict(self): ...
    def from_dict(self, d) -> None: ...
    @classmethod
    def deserialize(cls, v): ...

class ResourceStateEntity(BaseEntity):
    resource_state: Any

class IdentifiableEntity(ResourceStateEntity):
    id: Any

class BoundEntity(BaseEntity):
    bind_client: Any
    def __init__(self, bind_client: Any | None = ..., **kwargs) -> None: ...
    @classmethod
    def deserialize(cls, v, bind_client: Any | None = ...): ...
    def assert_bind_client(self) -> None: ...

class LoadableEntity(BoundEntity, IdentifiableEntity):
    def expand(self) -> None: ...

class Club(LoadableEntity):
    name: Any
    profile_medium: Any
    profile: Any
    description: Any
    club_type: Any
    sport_type: Any
    city: Any
    state: Any
    country: Any
    private: Any
    member_count: Any
    verified: Any
    url: Any
    featured: Any
    cover_photo: Any
    cover_photo_small: Any
    membership: Any
    admin: Any
    owner: Any
    @property
    def members(self): ...
    @property
    def activities(self): ...

class Gear(IdentifiableEntity):
    id: Any
    name: Any
    distance: Any
    primary: Any
    brand_name: Any
    model_name: Any
    description: Any
    @classmethod
    def deserialize(cls, v): ...

class Bike(Gear):
    frame_type: Any

class Shoe(Gear):
    nickname: Any
    converted_distance: Any
    retired: Any

class ActivityTotals(BaseEntity):
    achievement_count: Any
    count: Any
    distance: Any
    elapsed_time: Any
    elevation_gain: Any
    moving_time: Any

class AthleteStats(BaseEntity):
    biggest_ride_distance: Any
    biggest_climb_elevation_gain: Any
    recent_ride_totals: Any
    recent_run_totals: Any
    recent_swim_totals: Any
    ytd_ride_totals: Any
    ytd_run_totals: Any
    ytd_swim_totals: Any
    all_ride_totals: Any
    all_run_totals: Any
    all_swim_totals: Any

class Athlete(LoadableEntity):
    firstname: Any
    lastname: Any
    profile_medium: Any
    profile: Any
    city: Any
    state: Any
    country: Any
    sex: Any
    friend: Any
    follower: Any
    premium: Any
    summit: Any
    created_at: Any
    updated_at: Any
    approve_followers: Any
    badge_type_id: Any
    follower_count: Any
    friend_count: Any
    mutual_friend_count: Any
    athlete_type: Any
    date_preference: Any
    measurement_preference: Any
    email: Any
    clubs: Any
    bikes: Any
    shoes: Any
    super_user: Any
    email_language: Any
    weight: Any
    max_heartrate: Any
    username: Any
    description: Any
    instagram_username: Any
    offer_in_app_payment: Any
    global_privacy: Any
    receive_newsletter: Any
    email_kom_lost: Any
    dateofbirth: Any
    facebook_sharing_enabled: Any
    ftp: Any
    profile_original: Any
    premium_expiration_date: Any
    email_send_follower_notices: Any
    plan: Any
    agreed_to_terms: Any
    follower_request_count: Any
    email_facebook_twitter_friend_joins: Any
    receive_kudos_emails: Any
    receive_follower_feed_emails: Any
    receive_comment_emails: Any
    sample_race_distance: Any
    sample_race_time: Any
    membership: Any
    admin: Any
    owner: Any
    subscription_permissions: Any
    def is_authenticated_athlete(self): ...
    @property
    def friends(self): ...
    @property
    def followers(self): ...
    @property
    def stats(self): ...

class ActivityComment(LoadableEntity):
    activity_id: Any
    text: Any
    created_at: Any
    athlete: Any

class ActivityPhotoPrimary(LoadableEntity):
    id: Any
    unique_id: Any
    urls: Any
    source: Any
    use_primary_photo: Any

class ActivityPhotoMeta(BaseEntity):
    count: Any
    primary: Any
    use_primary_photo: Any

class ActivityPhoto(LoadableEntity):
    athlete_id: Any
    activity_id: Any
    activity_name: Any
    ref: Any
    uid: Any
    unique_id: Any
    caption: Any
    type: Any
    uploaded_at: Any
    created_at: Any
    created_at_local: Any
    location: Any
    urls: Any
    sizes: Any
    post_id: Any
    default_photo: Any
    source: Any

class ActivityKudos(LoadableEntity):
    firstname: Any
    lastname: Any
    profile_medium: Any
    profile: Any
    city: Any
    state: Any
    country: Any
    sex: Any
    friend: Any
    follower: Any
    premium: Any
    created_at: Any
    updated_at: Any
    approve_followers: Any

class ActivityLap(LoadableEntity):
    name: Any
    activity: Any
    athlete: Any
    elapsed_time: Any
    moving_time: Any
    start_date: Any
    start_date_local: Any
    distance: Any
    start_index: Any
    end_index: Any
    total_elevation_gain: Any
    average_speed: Any
    max_speed: Any
    average_cadence: Any
    average_watts: Any
    average_heartrate: Any
    max_heartrate: Any
    lap_index: Any
    device_watts: Any
    pace_zone: Any
    split: Any

class Map(IdentifiableEntity):
    id: Any
    polyline: Any
    summary_polyline: Any

class Split(BaseEntity):
    distance: Any
    elapsed_time: Any
    elevation_difference: Any
    moving_time: Any
    average_heartrate: Any
    split: Any
    pace_zone: Any
    average_speed: Any
    average_grade_adjusted_speed: Any

class SegmentExplorerResult(LoadableEntity):
    id: Any
    name: Any
    climb_category: Any
    climb_category_desc: Any
    avg_grade: Any
    start_latlng: Any
    end_latlng: Any
    elev_difference: Any
    distance: Any
    points: Any
    starred: Any
    @property
    def segment(self): ...

class AthleteSegmentStats(BaseEntity):
    effort_count: Any
    pr_elapsed_time: Any
    pr_date: Any

class AthletePrEffort(IdentifiableEntity):
    distance: Any
    elapsed_time: Any
    start_date: Any
    start_date_local: Any
    is_kom: Any

class Segment(LoadableEntity):
    name: Any
    activity_type: Any
    distance: Any
    average_grade: Any
    maximum_grade: Any
    elevation_high: Any
    elevation_low: Any
    start_latlng: Any
    end_latlng: Any
    start_latitude: Any
    end_latitude: Any
    start_longitude: Any
    end_longitude: Any
    climb_category: Any
    city: Any
    state: Any
    country: Any
    private: Any
    starred: Any
    athlete_segment_stats: Any
    created_at: Any
    updated_at: Any
    total_elevation_gain: Any
    map: Any
    effort_count: Any
    athlete_count: Any
    hazardous: Any
    star_count: Any
    pr_time: Any
    starred_date: Any
    athlete_pr_effort: Any
    elevation_profile: Any
    @property
    def leaderboard(self): ...

class SegmentEfforAchievement(BaseEntity):
    rank: Any
    type: Any
    type_id: Any

class BaseEffort(LoadableEntity):
    name: Any
    segment: Any
    activity: Any
    athlete: Any
    kom_rank: Any
    pr_rank: Any
    moving_time: Any
    elapsed_time: Any
    start_date: Any
    start_date_local: Any
    distance: Any
    average_watts: Any
    device_watts: Any
    average_heartrate: Any
    max_heartrate: Any
    average_cadence: Any
    start_index: Any
    end_index: Any
    achievements: Any

class BestEffort(BaseEffort): ...

class SegmentEffort(BaseEffort):
    hidden: Any
    device_watts: Any

class Activity(LoadableEntity):
    ALPINESKI: str
    BACKCOUNTRYSKI: str
    CANOEING: str
    CROSSCOUNTRYSKIING: str
    CROSSFIT: str
    EBIKERIDE: str
    ELLIPTICAL: str
    GOLF: str
    HANDCLYCLE: str
    HIKE: str
    ICESKATE: str
    INLINESKATE: str
    KAYAKING: str
    KITESURF: str
    NORDICSKI: str
    RIDE: str
    ROCKCLIMBING: str
    ROLLERSKI: str
    ROWING: str
    RUN: str
    SAIL: str
    SKATEBOARD: str
    SNOWBOARD: str
    SNOWSHOE: str
    SOCCER: str
    STAIRSTEPPER: str
    STANDUPPADDLING: str
    SURFING: str
    SWIM: str
    VELOMOBILE: str
    VIRTUALRIDE: str
    VIRTUALRUN: str
    WALK: str
    WEIGHTTRAINING: str
    WHEELCHAIR: str
    WINDSURF: str
    WORKOUT: str
    YOGA: str
    id: Any
    TYPES: Any
    guid: Any
    external_id: Any
    upload_id: Any
    athlete: Any
    name: Any
    distance: Any
    moving_time: Any
    elapsed_time: Any
    total_elevation_gain: Any
    elev_high: Any
    elev_low: Any
    type: Any
    start_date: Any
    start_date_local: Any
    timezone: Any
    utc_offset: Any
    start_latlng: Any
    end_latlng: Any
    location_city: Any
    location_state: Any
    location_country: Any
    start_latitude: Any
    start_longitude: Any
    achievement_count: Any
    pr_count: Any
    kudos_count: Any
    comment_count: Any
    athlete_count: Any
    photo_count: Any
    total_photo_count: Any
    map: Any
    trainer: Any
    commute: Any
    manual: Any
    private: Any
    flagged: Any
    gear_id: Any
    gear: Any
    average_speed: Any
    max_speed: Any
    device_watts: Any
    has_kudoed: Any
    best_efforts: Any
    segment_efforts: Any
    splits_metric: Any
    splits_standard: Any
    average_watts: Any
    weighted_average_watts: Any
    max_watts: Any
    suffer_score: Any
    has_heartrate: Any
    average_heartrate: Any
    max_heartrate: Any
    average_cadence: Any
    kilojoules: Any
    average_temp: Any
    device_name: Any
    embed_token: Any
    calories: Any
    description: Any
    workout_type: Any
    photos: Any
    instagram_primary_photo: Any
    partner_logo_url: Any
    partner_brand_tag: Any
    from_accepted_tag: Any
    segment_leaderboard_opt_out: Any
    highlighted_kudosers: Any
    laps: Any
    @property
    def comments(self): ...
    @property
    def zones(self): ...
    @property
    def kudos(self): ...
    @property
    def full_photos(self): ...
    @property
    def related(self): ...

class SegmentLeaderboardEntry(BoundEntity):
    athlete_name: Any
    elapsed_time: Any
    moving_time: Any
    start_date: Any
    start_date_local: Any
    rank: Any

class SegmentLeaderboard(Sequence, BoundEntity):
    entry_count: Any
    effort_count: Any
    kom_type: Any
    entries: Any
    def __iter__(self): ...
    def __len__(self): ...
    def __contains__(self, k): ...
    def __getitem__(self, k): ...

class DistributionBucket(BaseEntity):
    max: Any
    min: Any
    time: Any

class BaseActivityZone(LoadableEntity):
    distribution_buckets: Any
    type: Any
    sensor_based: Any
    @classmethod
    def deserialize(cls, v, bind_client: Any | None = ...): ...

class HeartrateActivityZone(BaseActivityZone):
    score: Any
    points: Any
    custom_zones: Any
    max: Any

class PaceActivityZone(BaseActivityZone):
    score: Any
    sample_race_distance: Any
    sample_race_time: Any

class PowerActivityZone(BaseActivityZone):
    bike_weight: Any
    athlete_weight: Any

class Stream(LoadableEntity):
    type: Any
    data: Any
    series_type: Any
    original_size: Any
    resolution: Any

class RunningRace(LoadableEntity):
    name: Any
    id: Any
    running_race_type: Any
    distance: Any
    start_date_local: Any
    city: Any
    state: Any
    country: Any
    description: Any
    route_ids: Any
    measurement_preference: Any
    url: Any
    website_url: Any
    status: Any

class Route(LoadableEntity):
    name: Any
    description: Any
    athlete: Any
    distance: Any
    elevation_gain: Any
    map: Any
    type: Any
    sub_type: Any
    private: Any
    starred: Any
    timestamp: Any

class Subscription(LoadableEntity):
    OBJECT_TYPE_ACTIVITY: str
    ASPECT_TYPE_CREATE: str
    VERIFY_TOKEN_DEFAULT: str
    application_id: Any
    object_type: Any
    aspect_type: Any
    callback_url: Any
    created_at: Any
    updated_at: Any

class SubscriptionCallback(LoadableEntity):
    hub_mode: Any
    hub_verify_token: Any
    hub_challenge: Any
    def validate(self, verify_token=...) -> None: ...

class SubscriptionUpdate(LoadableEntity):
    subscription_id: Any
    owner_id: Any
    object_id: Any
    object_type: Any
    aspect_type: Any
    event_time: Any
    updates: Any
