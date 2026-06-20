# Create a Docker container for psql database

docker run --name hajj-postgres -e POSTGRES_DB=hajj -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=123456 -p 5432:5432 -d postgres:16

python manage.py makemigrations
python manage.py migrate

# new company create data sequence
python manage.py create_fake_company
python manage.py create_tent
python manage.py create_user
python manage.py create_tentairqualityrecord
python manage.py create_tentwatertank
python manage.py create_watertanksensorhistory
python manage.py create_environmentsensor
python manage.py create_weight_sensor
python manage.py create_environmentsensorrecord
python manage.py create_cameras


python manage.py create_counterhistory
python manage.py create_clean_indicator_history
python manage.py create_guardpresencehistroy
python manage.py create_cameraheartbeat
python manage.py create_kitchenviolationreport //test

python manage.py generate_fake_weight_conditions




--------------Rename Tent and Camera SN
python manage.py rename_tent_names
python manage.py rename_camera_sn

python manage.py create_user
python manage.py create_tentwatertank
python manage.py create_environmentsensor
python manage.py create_unassign_sensor

python manage.py create_weight_sensor
python manage.py create_camera_type
python manage.py create_cameras


python manage.py assign_tent_nationalities
==================================================
Import Country

python manage.py import_countries

python manage.py create_cameratypestatus.py

updated


# For fake guard create
python manage.py generate_guard
python manage.py guard_null_fillup
python manage.py generate_people_count
python manage.py w_order_weight
python manage.py dummy_data_sensor

python manage.py camp_1_data_sensor

python manage.py update_sensor_nbr
python manage.py collect_sensor_data
python manage.py data_update

python manage.py nbr_update_sheet

 


python manage.py update_sensor_records


python manage.py insert_hajj_camp_env_data3_Arafat
python manage.py fill_missing_temperature