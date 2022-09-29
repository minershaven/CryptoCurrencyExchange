from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render
from wallet.models import Token, Wallet, History
from .forms import BuySellForm
from django.views.generic.detail import DetailView
import plotly.offline as opy
import plotly.graph_objs as go


EXCHANGE_PK = 13
USDT_PK = 3
TRANSACTION_FEE = 5


@login_required
def home(request):
    tokens = Token.objects.all()
    history = History.objects.filter(token_id='1').order_by('date_time')

    prices = [data.price for data in history]
    date_times = [f"{data.date_time}" for data in history]
    #trace1 = go.Scatter(x=date_times, y=prices, marker={'color': 'red', 'symbol': 104, 'size': 10},
                        #mode="lines", name='1st Trace')

    #layout = go.Layout(title="Meine Daten", xaxis={'title': 'x1'}, yaxis={'title': 'x2'})
    #figure = go.Figure(data=trace1, layout=layout)
    fig = go.Figure([go.Scatter(x=date_times, y=prices)])
    graph = fig.to_html(full_html=False, default_height=500, default_width=700)

    return render(request, 'dashboard/home.html', {'title': 'Dashboard',
                                                   'subtitle': 'Home',
                                                   'tokens': tokens,
                                                   'prices': prices,
                                                   'date_times': date_times,
                                                   'graph': graph})


class TokenDetailView(DetailView):
    model = Token
    template_name = "dashboard/token.html"
    slug_field = 'name'

    def get_context_data(self, request, **kwargs):
        context = super().get_context_data(**kwargs)

        user_pk = request.user.pk
        user_token_wallet = Wallet.objects.get(owner=user_pk, token=self.object.pk)
        user_usdt_wallet = Wallet.objects.get(owner=user_pk, token=USDT_PK)
        context['form'] = BuySellForm()
        context['user_token_wallet'] = user_token_wallet
        context['user_usdt_wallet'] = user_usdt_wallet
        context['tokens'] = Token.objects.all()
        context['title'] = self.object.name.capitalize()
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(request=request, object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(request=request, object=self.object)
        context['form'] = BuySellForm(request.POST)

        context = self.form_validation(context, request)

        return self.render_to_response(context)

    def form_validation(self, context, request):

        form = context['form']
        amount_buyer = float(form.data['amount'])
        transaction_price = self.object.actual_price * amount_buyer + TRANSACTION_FEE
        user_token_wallet = context['user_token_wallet']
        user_usdt_wallet = context['user_usdt_wallet']
        exchange_token_wallet = Wallet.objects.get(owner=EXCHANGE_PK, token=self.object.pk)
        exchange_usdt_wallet = Wallet.objects.get(owner=EXCHANGE_PK, token=USDT_PK)

        if 'sell_token' in request.POST:

            if form.is_valid() and amount_buyer <= user_token_wallet.quantity:

                if transaction_price <= exchange_usdt_wallet.quantity:
                    user_token_wallet.quantity = user_token_wallet.quantity - amount_buyer
                    user_usdt_wallet.quantity = user_usdt_wallet.quantity + transaction_price

                    exchange_token_wallet.quantity = exchange_token_wallet.quantity + amount_buyer
                    exchange_usdt_wallet.quantity = exchange_usdt_wallet.quantity - transaction_price

                    user_token_wallet.save()
                    user_usdt_wallet.save()
                    exchange_token_wallet.save()
                    exchange_usdt_wallet.save()

                    context['user_usdt_wallet'] = user_token_wallet
                    context['user_usdt_wallet'] = user_usdt_wallet

                    messages.success(request, f"You sell {amount_buyer} BTC")
                else:
                    messages.error(request, extra_tags="danger",
                                   message=f"The operation can not be completed - stock exchange doesn't have the resources")
            else:
                messages.warning(request, f"The operation can not be completed - You are too poor")

        elif 'buy_token' in request.POST:

            if form.is_valid() and transaction_price <= user_usdt_wallet.quantity:

                if amount_buyer <= exchange_token_wallet.quantity:
                    user_token_wallet.quantity = user_token_wallet.quantity + amount_buyer
                    user_usdt_wallet.quantity = user_usdt_wallet.quantity - transaction_price

                    exchange_token_wallet.quantity = exchange_token_wallet.quantity - amount_buyer
                    exchange_usdt_wallet.quantity = exchange_usdt_wallet.quantity + transaction_price

                    user_token_wallet.save()
                    user_usdt_wallet.save()
                    exchange_token_wallet.save()
                    exchange_usdt_wallet.save()

                    context['user_usdt_wallet'] = user_token_wallet
                    context['user_usdt_wallet'] = user_usdt_wallet

                    messages.success(request, f"You bought {amount_buyer} BTC")
                else:
                    messages.error(request, f"The operation can not be completed - stock exchange doesn't have the resources")
            else:
                messages.warning(request, f"The operation can not be completed - You are too poor")

        return context

