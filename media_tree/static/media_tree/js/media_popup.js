;(function ( $, window, document, undefined ) {

    var $modal = $(".avgrund-popin").first();

    $(function(){
        $(".mediatree-btn-select").avgrund({
            afterLoad: function(elem) {
                $(".avgrund-popin").load('/admin/media_tree/filenode/ #content');
            },
            enableStackAnimation: true,
        });

        $(".mediatree-btn-upload").avgrund({
            afterLoad: function(elem) {
                $(".avgrund-popin").load('/admin/media_tree/filenode/add/ #content');
            },
            enableStackAnimation: true,
        });
    })

})(django.jQuery, window, document);