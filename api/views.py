from api.permissions import IsOwnerOrReadOnly
from christmas_crowdsource.settings import STRIPE_API_KEY
from rest_framework import permissions
from api.serializers import UserSerializer, WishListSerializer, ItemSerializer, \
    PledgeSerializer, CreatePledgeSerializer
from christmas_list.models import WishList, Item, Pledge
from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import generics
import stripe


class ListUsers(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = (permissions.IsAdminUser, )


class CreateUser(generics.CreateAPIView):
    serializer_class = UserSerializer


class ListCreateWishLists(generics.ListCreateAPIView):
    queryset = WishList.objects.all()
    serializer_class = WishListSerializer
    # permission_classes = (permissions.IsAuthenticatedOrReadOnly, )

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)

    def get_queryset(self):
        qs =  super().get_queryset()
        user_id = self.request.query_params.get('user-id', None)
        if user_id:
            qs = qs.filter(user__id=user_id)
        return qs


class ListCreateItems(generics.ListCreateAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    # permission_classes = (permissions.IsAuthenticatedOrReadOnly, )



class ListPledges(generics.ListAPIView):
    queryset = Pledge.objects.all()
    serializer_class = PledgeSerializer
    # permission_classes = (permissions.IsAuthenticatedOrReadOnly, )

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user-id', None)
        if user_id:
            qs = qs.filter(user__id=user_id)
        return qs


class DetailUpdateWishList(generics.RetrieveUpdateDestroyAPIView):
    queryset = WishList.objects.all()
    serializer_class = WishListSerializer

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


    # permission_classes = (permissions.IsAuthenticatedOrReadOnly,
    #                       IsOwnerOrReadOnly)

    def perform_update(self, serializer):
        super().perform_update(serializer)


class DetailUpdateItem(generics.RetrieveUpdateDestroyAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    # permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class DetailUpdatePledge(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pledge.objects.all()
    serializer_class = PledgeSerializer
    # permission_classes = (permissions.IsAuthenticatedOrReadOnly,
    #                       IsOwnerOrReadOnly)


class CreatePledge(generics.CreateAPIView):
    serializer_class = CreatePledgeSerializer

    def stripe_charge(self, token, amount):
        stripe.api_key = STRIPE_API_KEY
        if isinstance(amount, str):
            amount = float(amount)
        amount *= 100
        amount = int(amount)

        # Create the charge on Stripe's servers -
        # this will charge the user's card
        try:
            charge = stripe.Charge.create(
              amount=amount,
              currency="usd",
              source=token,
              description="Example charge"
            )

            return charge['id']

        except stripe.error.CardError as e:
            # The card has been declined
            pass


    def perform_create(self, serializer):
        user = self.request.user
        item_id = self.kwargs['pk']
        item = Item.objects.get(pk=item_id)
        amount = serializer.initial_data['amount']
        token = serializer.initial_data['token']
        charge_id = self.stripe_charge(token, amount)
        serializer.save(user=user, item=item, amount=amount,
                        charge_id=charge_id)
        if item.amount_needed <= 0:
            item.is_funded = True
            item.save()
