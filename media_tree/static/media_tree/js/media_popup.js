;(function ( $, window, document, undefined ) {

    var $modal = $(".avgrund-popin").first();

    $(function(){
        $(".mediatree-btn-select").avgrund({
            afterLoad: function(elem) {
                $(".avgrund-popin").load('/admin/cms/card/ #content');
            },
            enableStackAnimation: true,
        });

        $(".mediatree-btn-upload").avgrund({
            afterLoad: function(elem) {
                $(".avgrund-popin").load('/admin/cms/card/add/ #content');
            },
            enableStackAnimation: true,
        });
    })

})(django.jQuery, window, document);