import abc
from _typeshed import Incomplete
from collections.abc import Sequence
from stravalib import exc as exc
from stravalib.attributes import Attribute as Attribute, ChoicesAttribute as ChoicesAttribute, DETAILED as DETAILED, DateAttribute as DateAttribute, EntityAttribute as EntityAttribute, EntityCollection as EntityCollection, LocationAttribute as LocationAttribute, META as META, SUMMARY as SUMMARY, TimeIntervalAttribute as TimeIntervalAttribute, TimestampAttribute as TimestampAttribute, TimezoneAttribute as TimezoneAttribute

class BaseEntity(metaclass=abc.ABCMeta):
    log: Incomplete
    def __init__(self, **kwargs) -> None: ...
    def to_dict(self): ...
    def from_dict(self, d) -> None: ...
    @classmethod
    def deserialize(cls, v): ...

class ResourceStateEntity(BaseEntity):
    resource_state: Incomplete

class IdentifiableEntity(ResourceStateEntity):
    id: Incomplete

class BoundEntity(BaseEntity):
    bind_client: Incomplete
    def __init__(self, bind_client: Incomplete | None = ..., **kwargs) -> None: ...
    @classmethod
    def deserialize(cls, v, bind_client: Incomplete | None = ...): ...
    def assert_bind_client(self) -> None: ...

class LoadableEntity(BoundEntity, IdentifiableEntity):
    def expand(self) -> None: ...

class Club(LoadableEntity):
    name: Incomplete
    profile_medium: Incomplete
    profile: Incomplete
    description: Incomplete
    club_type: Incomplete
    sport_type: Incomplete
    city: Incomplete
    state: Incomplete
    country: Incomplete
    private: Incomplete
    member_count: Incomplete
    verified: Incomplete
    url: Incomplete
    featured: Incomplete
    cover_photo: Incomplete
    cover_photo_small: Incomplete
    membership: Incomplete
    admin: Incomplete
    owner: Incomplete
    @property
    def members(self): ...
    @property
    def activities(self): ...

class Gear(IdentifiableEntity):
    id: Incomplete
    name: Incomplete
    distance: Incomplete
    primary: Incomplete
    brand_name: Incomplete
    model_name: Incomplete
    description: Incomplete
    @classmethod
    def deserialize(cls, v): ...

class Bike(Gear):
    frame_type: Incomplete
    nickname: Incomplete
    converted_distance: Incomplete
    retired: Incomplete

class Shoe(Gear):
    nickname: Incomplete
    converted_distance: Incomplete
    retired: Incomplete

class ActivityTotals(BaseEntity):
    achievement_count: Incomplete
    count: Incomplete
    distance: Incomplete
    elapsed_time: Incomplete
    elevation_gain: Incomplete
    moving_time: Incomplete

class AthleteStats(BaseEntity):
    biggest_ride_distance: Incomplete
    biggest_climb_elevation_gain: Incomplete
    recent_ride_totals: Incomplete
    recent_run_totals: Incomplete
    recent_swim_totals: Incomplete
    ytd_ride_totals: Incomplete
    ytd_run_totals: Incomplete
    ytd_swim_totals: Incomplete
    all_ride_totals: Incomplete
    all_run_totals: Incomplete
    all_swim_totals: Incomplete

class Athlete(LoadableEntity):
    firstname: Incomplete
    lastname: Incomplete
    profile_medium: Incomplete
    profile: Incomplete
    city: Incomplete
    state: Incomplete
    country: Incomplete
    sex: Incomplete
    friend: Incomplete
    follower: Incomplete
    premium: Incomplete
    summit: Incomplete
    created_at: Incomplete
    updated_at: Incomplete
    approve_followers: Incomplete
    badge_type_id: Incomplete
    follower_count: Incomplete
    friend_count: Incomplete
    mutual_friend_count: Incomplete
    athlete_type: Incomplete
    date_preference: Incomplete
    measurement_preference: Incomplete
    email: Incomplete
    clubs: Incomplete
    bikes: Incomplete
    shoes: Incomplete
    super_user: Incomplete
    email_language: Incomplete
    weight: Incomplete
    max_heartrate: Incomplete
    username: Incomplete
    description: Incomplete
    instagram_username: Incomplete
    offer_in_app_payment: Incomplete
    global_privacy: Incomplete
    receive_newsletter: Incomplete
    email_kom_lost: Incomplete
    dateofbirth: Incomplete
    facebook_sharing_enabled: Incomplete
    ftp: Incomplete
    profile_original: Incomplete
    premium_expiration_date: Incomplete
    email_send_follower_notices: Incomplete
    plan: Incomplete
    agreed_to_terms: Incomplete
    follower_request_count: Incomplete
    email_facebook_twitter_friend_joins: Incomplete
    receive_kudos_emails: Incomplete
    receive_follower_feed_emails: Incomplete
    receive_comment_emails: Incomplete
    sample_race_distance: Incomplete
    sample_race_time: Incomplete
    membership: Incomplete
    admin: Incomplete
    owner: Incomplete
    subscription_permissions: Incomplete
    def is_authenticated_athlete(self): ...
    @property
    def friends(self): ...
    @property
    def followers(self): ...
    @property
    def stats(self): ...

class ActivityComment(LoadableEntity):
    activity_id: Incomplete
    text: Incomplete
    created_at: Incomplete
    athlete: Incomplete

class ActivityPhotoPrimary(LoadableEntity):
    id: Incomplete
    unique_id: Incomplete
    urls: Incomplete
    source: Incomplete
    use_primary_photo: Incomplete

class ActivityPhotoMeta(BaseEntity):
    count: Incomplete
    primary: Incomplete
    use_primary_photo: Incomplete

class ActivityPhoto(LoadableEntity):
    athlete_id: Incomplete
    activity_id: Incomplete
    activity_name: Incomplete
    ref: Incomplete
    uid: Incomplete
    unique_id: Incomplete
    caption: Incomplete
    type: Incomplete
    uploaded_at: Incomplete
    created_at: Incomplete
    created_at_local: Incomplete
    location: Incomplete
    urls: Incomplete
    sizes: Incomplete
    post_id: Incomplete
    default_photo: Incomplete
    source: Incomplete

class ActivityKudos(LoadableEntity):
    firstname: Incomplete
    lastname: Incomplete
    profile_medium: Incomplete
    profile: Incomplete
    city: Incomplete
    state: Incomplete
    country: Incomplete
    sex: Incomplete
    friend: Incomplete
    follower: Incomplete
    premium: Incomplete
    created_at: Incomplete
    updated_at: Incomplete
    approve_followers: Incomplete

class ActivityLap(LoadableEntity):
    name: Incomplete
    activity: Incomplete
    athlete: Incomplete
    elapsed_time: Incomplete
    moving_time: Incomplete
    start_date: Incomplete
    start_date_local: Incomplete
    distance: Incomplete
    start_index: Incomplete
    end_index: Incomplete
    total_elevation_gain: Incomplete
    average_speed: Incomplete
    max_speed: Incomplete
    average_cadence: Incomplete
    average_watts: Incomplete
    average_heartrate: Incomplete
    max_heartrate: Incomplete
    lap_index: Incomplete
    device_watts: Incomplete
    pace_zone: Incomplete
    split: Incomplete

class Map(IdentifiableEntity):
    id: Incomplete
    polyline: Incomplete
    summary_polyline: Incomplete

class Split(BaseEntity):
    distance: Incomplete
    elapsed_time: Incomplete
    elevation_difference: Incomplete
    moving_time: Incomplete
    average_heartrate: Incomplete
    split: Incomplete
    pace_zone: Incomplete
    average_speed: Incomplete
    average_grade_adjusted_speed: Incomplete

class SegmentExplorerResult(LoadableEntity):
    id: Incomplete
    name: Incomplete
    climb_category: Incomplete
    climb_category_desc: Incomplete
    avg_grade: Incomplete
    start_latlng: Incomplete
    end_latlng: Incomplete
    elev_difference: Incomplete
    distance: Incomplete
    points: Incomplete
    starred: Incomplete
    @property
    def segment(self): ...

class AthleteSegmentStats(BaseEntity):
    effort_count: Incomplete
    pr_elapsed_time: Incomplete
    pr_date: Incomplete

class AthletePrEffort(IdentifiableEntity):
    distance: Incomplete
    elapsed_time: Incomplete
    start_date: Incomplete
    start_date_local: Incomplete
    is_kom: Incomplete

class Segment(LoadableEntity):
    name: Incomplete
    activity_type: Incomplete
    distance: Incomplete
    average_grade: Incomplete
    maximum_grade: Incomplete
    elevation_high: Incomplete
    elevation_low: Incomplete
    start_latlng: Incomplete
    end_latlng: Incomplete
    start_latitude: Incomplete
    end_latitude: Incomplete
    start_longitude: Incomplete
    end_longitude: Incomplete
    climb_category: Incomplete
    city: Incomplete
    state: Incomplete
    country: Incomplete
    private: Incomplete
    starred: Incomplete
    athlete_segment_stats: Incomplete
    created_at: Incomplete
    updated_at: Incomplete
    total_elevation_gain: Incomplete
    map: Incomplete
    effort_count: Incomplete
    athlete_count: Incomplete
    hazardous: Incomplete
    star_count: Incomplete
    pr_time: Incomplete
    starred_date: Incomplete
    athlete_pr_effort: Incomplete
    elevation_profile: Incomplete
    @property
    def leaderboard(self): ...

class SegmentEfforAchievement(BaseEntity):
    rank: Incomplete
    type: Incomplete
    type_id: Incomplete

class BaseEffort(LoadableEntity):
    name: Incomplete
    segment: Incomplete
    activity: Incomplete
    athlete: Incomplete
    kom_rank: Incomplete
    pr_rank: Incomplete
    moving_time: Incomplete
    elapsed_time: Incomplete
    start_date: Incomplete
    start_date_local: Incomplete
    distance: Incomplete
    average_watts: Incomplete
    device_watts: Incomplete
    average_heartrate: Incomplete
    max_heartrate: Incomplete
    average_cadence: Incomplete
    start_index: Incomplete
    end_index: Incomplete
    achievements: Incomplete

class BestEffort(BaseEffort): ...

class SegmentEffort(BaseEffort):
    hidden: Incomplete
    device_watts: Incomplete

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
    id: Incomplete
    TYPES: Incomplete
    guid: Incomplete
    external_id: Incomplete
    upload_id: Incomplete
    athlete: Incomplete
    name: Incomplete
    distance: Incomplete
    moving_time: Incomplete
    elapsed_time: Incomplete
    total_elevation_gain: Incomplete
    elev_high: Incomplete
    elev_low: Incomplete
    type: Incomplete
    start_date: Incomplete
    start_date_local: Incomplete
    timezone: Incomplete
    utc_offset: Incomplete
    start_latlng: Incomplete
    end_latlng: Incomplete
    location_city: Incomplete
    location_state: Incomplete
    location_country: Incomplete
    start_latitude: Incomplete
    start_longitude: Incomplete
    achievement_count: Incomplete
    pr_count: Incomplete
    kudos_count: Incomplete
    comment_count: Incomplete
    athlete_count: Incomplete
    photo_count: Incomplete
    total_photo_count: Incomplete
    map: Incomplete
    trainer: Incomplete
    commute: Incomplete
    manual: Incomplete
    private: Incomplete
    flagged: Incomplete
    gear_id: Incomplete
    gear: Incomplete
    average_speed: Incomplete
    max_speed: Incomplete
    device_watts: Incomplete
    has_kudoed: Incomplete
    best_efforts: Incomplete
    segment_efforts: Incomplete
    splits_metric: Incomplete
    splits_standard: Incomplete
    average_watts: Incomplete
    weighted_average_watts: Incomplete
    max_watts: Incomplete
    suffer_score: Incomplete
    has_heartrate: Incomplete
    average_heartrate: Incomplete
    max_heartrate: Incomplete
    average_cadence: Incomplete
    kilojoules: Incomplete
    average_temp: Incomplete
    device_name: Incomplete
    embed_token: Incomplete
    calories: Incomplete
    description: Incomplete
    workout_type: Incomplete
    photos: Incomplete
    instagram_primary_photo: Incomplete
    partner_logo_url: Incomplete
    partner_brand_tag: Incomplete
    from_accepted_tag: Incomplete
    segment_leaderboard_opt_out: Incomplete
    highlighted_kudosers: Incomplete
    laps: Incomplete
    hide_from_home: Incomplete
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
    athlete_name: Incomplete
    elapsed_time: Incomplete
    moving_time: Incomplete
    start_date: Incomplete
    start_date_local: Incomplete
    rank: Incomplete

class SegmentLeaderboard(Sequence, BoundEntity):
    entry_count: Incomplete
    effort_count: Incomplete
    kom_type: Incomplete
    entries: Incomplete
    def __iter__(self): ...
    def __len__(self) -> int: ...
    def __contains__(self, k) -> bool: ...
    def __getitem__(self, k): ...

class DistributionBucket(BaseEntity):
    max: Incomplete
    min: Incomplete
    time: Incomplete

class BaseActivityZone(LoadableEntity):
    distribution_buckets: Incomplete
    type: Incomplete
    sensor_based: Incomplete
    @classmethod
    def deserialize(cls, v, bind_client: Incomplete | None = ...): ...

class HeartrateActivityZone(BaseActivityZone):
    score: Incomplete
    points: Incomplete
    custom_zones: Incomplete
    max: Incomplete

class PaceActivityZone(BaseActivityZone):
    score: Incomplete
    sample_race_distance: Incomplete
    sample_race_time: Incomplete

class PowerActivityZone(BaseActivityZone):
    bike_weight: Incomplete
    athlete_weight: Incomplete

class Stream(LoadableEntity):
    type: Incomplete
    data: Incomplete
    series_type: Incomplete
    original_size: Incomplete
    resolution: Incomplete

class RunningRace(LoadableEntity):
    name: Incomplete
    id: Incomplete
    running_race_type: Incomplete
    distance: Incomplete
    start_date_local: Incomplete
    city: Incomplete
    state: Incomplete
    country: Incomplete
    description: Incomplete
    route_ids: Incomplete
    measurement_preference: Incomplete
    url: Incomplete
    website_url: Incomplete
    status: Incomplete

class Route(LoadableEntity):
    name: Incomplete
    description: Incomplete
    athlete: Incomplete
    distance: Incomplete
    elevation_gain: Incomplete
    map: Incomplete
    type: Incomplete
    sub_type: Incomplete
    private: Incomplete
    starred: Incomplete
    timestamp: Incomplete

class Subscription(LoadableEntity):
    OBJECT_TYPE_ACTIVITY: str
    ASPECT_TYPE_CREATE: str
    VERIFY_TOKEN_DEFAULT: str
    application_id: Incomplete
    object_type: Incomplete
    aspect_type: Incomplete
    callback_url: Incomplete
    created_at: Incomplete
    updated_at: Incomplete

class SubscriptionCallback(LoadableEntity):
    hub_mode: Incomplete
    hub_verify_token: Incomplete
    hub_challenge: Incomplete
    def validate(self, verify_token=...) -> None: ...

class SubscriptionUpdate(LoadableEntity):
    subscription_id: Incomplete
    owner_id: Incomplete
    object_id: Incomplete
    object_type: Incomplete
    aspect_type: Incomplete
    event_time: Incomplete
    updates: Incomplete
