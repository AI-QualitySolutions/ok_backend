from rest_framework import serializers
from weight.models import OrderWeight, WeightConditions


class OrderWeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderWeight
        fields = ('device_num', 'weight', 'date',
                  'secret', "weight_sensor")

class WeightConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightConditions
        fields = ('start_date', 'end_date', 'breakfast_start', 'breakfast_end', 'lunch_start', 'lunch_end', 'dinner_start', 'dinner_end', 'breakfast_weight_accepted', 'lunch_weight_accepted', 'dinner_weight_accepted')

class TentFoodWeightsSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    capacity = serializers.IntegerField()
    breakfast_rejected_meals = serializers.IntegerField()
    breakfast_accepted_meals = serializers.IntegerField()
    lunch_rejected_meals = serializers.IntegerField()
    lunch_accepted_meals = serializers.IntegerField()
    dinner_rejected_meals = serializers.IntegerField()
    dinner_accepted_meals = serializers.IntegerField()
    breakfast_average_weight = serializers.FloatField()
    lunch_average_weight = serializers.FloatField()
    dinner_average_weight = serializers.FloatField()
    total_rejected_meals = serializers.FloatField()
    total_accepted_meals = serializers.FloatField()