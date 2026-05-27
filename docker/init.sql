create schema if not exists raw;
create schema if not exists staging;
create schema if not exists intermediate;
create schema if not exists analytics;

comment on schema raw is 'Raw synthetic operational data for online retail order management.';
comment on schema analytics is 'Kimball dimensional warehouse and BI marts.';
