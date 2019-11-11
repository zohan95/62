import datetime
from time import strptime, strftime

from django.shortcuts import reverse, redirect, render

from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from webapp.models import Product, OrderProduct, Order


class StatViewMixin:
    def stat_update(self, request, page):
        list_history = request.session.get('list_history', [])
        last_page = request.session.get('last_page')
        last_time = request.session.get('last_time')
        if last_page:
            for i in list_history:
                if last_page in i[0]:
                    i[1] += (datetime.datetime.now() - datetime.datetime.strptime(last_time,
                                                                                  '%d-%m-%Y, %H:%M:%S')).seconds
                    i[2] += 1
                    request.session['last_time'] = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
                    request.session['last_page'] = page
                    break
            else:
                list_history.append([last_page, (datetime.datetime.now() - datetime.datetime.strptime(last_time,
                                                                                                      '%d-%m-%Y, %H:%M:%S')).seconds,
                                     1])
        else:
            request.session['last_page'] = page
            request.session['last_time'] = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
        request.session['list_history'] = list_history
        print(request.session['list_history'])


class IndexView(ListView, StatViewMixin):
    model = Product
    template_name = 'index.html'

    def get(self, request, *args, **kwargs):
        super().stat_update(request, request.path)
        return super().get(request, *args, **kwargs)


class ProductView(DetailView, StatViewMixin):
    model = Product
    template_name = 'product/detail.html'

    def get(self, request, *args, **kwargs):
        super().stat_update(request, request.path)
        return super().get(request, *args, **kwargs)


class ProductCreateView(CreateView, StatViewMixin):
    model = Product
    template_name = 'product/create.html'
    fields = ('name', 'category', 'price', 'photo')
    success_url = reverse_lazy('webapp:index')

    def get(self, request, *args, **kwargs):
        super().stat_update(request, request.path)
        return super().get(request, *args, **kwargs)


class BasketChangeView(View):
    def get(self, request, *args, **kwargs):
        products = request.session.get('products', [])

        pk = request.GET.get('pk')
        action = request.GET.get('action')
        next_url = request.GET.get('next', reverse('webapp:index'))

        if action == 'add':
            products.append(pk)
        else:
            for product_pk in products:
                if product_pk == pk:
                    products.remove(product_pk)
                    break

        request.session['products'] = products
        request.session['products_count'] = len(products)

        return redirect(next_url)


class BasketView(CreateView, StatViewMixin):
    model = Order
    fields = ('first_name', 'last_name', 'phone', 'email')
    template_name = 'product/basket.html'
    success_url = reverse_lazy('webapp:index')

    def get_context_data(self, **kwargs):
        basket, basket_total = self._prepare_basket()
        kwargs['basket'] = basket
        kwargs['basket_total'] = basket_total
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        if self._basket_empty():
            form.add_error(None, 'В корзине отсутствуют товары!')
            return self.form_invalid(form)
        response = super().form_valid(form)
        self._save_order_products()
        self._clean_basket()
        return response

    def _prepare_basket(self):
        totals = self._get_totals()
        basket = []
        basket_total = 0
        for pk, qty in totals.items():
            product = Product.objects.get(pk=int(pk))
            total = product.price * qty
            basket_total += total
            basket.append({'product': product, 'qty': qty, 'total': total})
        return basket, basket_total

    def _get_totals(self):
        products = self.request.session.get('products', [])
        totals = {}
        for product_pk in products:
            if product_pk not in totals:
                totals[product_pk] = 0
            totals[product_pk] += 1
        return totals

    def _basket_empty(self):
        products = self.request.session.get('products', [])
        return len(products) == 0

    def _save_order_products(self):
        totals = self._get_totals()
        for pk, qty in totals.items():
            OrderProduct.objects.create(product_id=pk, order=self.object, amount=qty)

    def _clean_basket(self):
        if 'products' in self.request.session:
            self.request.session.pop('products')
        if 'products_count' in self.request.session:
            self.request.session.pop('products_count')


class StatView(View):
    def get(self, request):
        list_history = request.session.get('list_history', [])
        summ = 0
        if list_history:
            for i in list_history:
                summ += i[1]
        return render(request, 'product/stat.html', {'summ': summ, 'stat': list_history})
