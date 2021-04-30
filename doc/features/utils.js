$(document).ready( () => {
    // make images zoomable
    makeImagesZoomable( $("body") ) ;
} ) ;

// --------------------------------------------------------------------

function makeImagesZoomable( $elem )
{
    // look for images that have been marked as zoomable, and make it so
    $elem.find( "img.imageZoom" ).each( function() {
        $(this).wrap( $( "<a>", {
            class: "imageZoom",
            href: $(this).attr( "src" ),
            title: "Click to zoom",
            onFocus: "javascript:this.blur()"
        } ) ) ;
    } ) ;
    $elem.find( "img.imageZoom" ).imageZoom( $ ) ;
}
