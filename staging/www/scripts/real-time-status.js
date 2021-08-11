function RealTimeStatus () {
   this.frequency = 5000;
   this.callback = null;
   this.request = 0;

   this.parse = function (data) {
      obj = $.parseJSON(data);

      return obj;
   };

   this.fetch = function () {
      var me = this;
      me.request++;

      if (typeof this.esource === 'undefined') {
         $.ajax({
            'url': '/status.php?r=' + me.request
         }).done(function (data) {
            if (me.callback != null) {
               me.callback(me.parse(data));
               window.setTimeout(me.fetch.bind(me), me.frequency);
            }
         });
      }
   };

   if (!!window.EventSource) {
      var me = this;
      this.esource = new EventSource('/fast_status.php');
      this.esource.addEventListener('message', function (e) {
         if (!me.callback) return;
         me.callback(me.parse(e.data));
      }, false);
   } else {
      this.fetch();
   }
};

stat = new RealTimeStatus();
stat.callback = function (info) {
   node = $('#status');

   if (node.find('div').length == 0) {
      for (var index in info.products) {
         product = info.products[index]
         node.append(
            '<div id="product-' + product.id + '" class="product-wrapper"><div class="product-display"></div></div>'
         );
      }
   }

   for (var index in info.products) {
      product = info.products[index]
      prodnode = node.find('#product-' + product.id + ' .product-display');
      if (prodnode.length == 0) return;

      subtitle = product.state;
      used_by = product.account;

      if (used_by !== false) {
         used_by = '<h2>' + used_by + '</h2>';
      } else {
         used_by = product.prevaccount;
         if (used_by !== false) {
            used_by = '<h2><i>Last used by ' + used_by + '</i></h2>';
         } else {
            used_by = '<h2>&ndash;</h2>';
         }
      }

      prodnode.replaceWith(
         '<div class="product-display">' +
            '<h1>' + product.id + ' ' + product.name + '</h1>' +
            '<h2>' + product.state + '</h2>' +
            used_by +
            '<p class="totalizer">' + product.totalizer + ' ' + info.unit + '</p>' +
         '</div>'
      );
   };
}

