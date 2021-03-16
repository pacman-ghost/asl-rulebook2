// --------------------------------------------------------------------

const _HILITE_REGEXES = [
    new RegExp("!@:","g"), new RegExp(":@!","g"),
] ;

export function fixupSearchHilites( val )
{
    // NOTE: The search engine highlights search tems in the returned search content using special markers.
    // We convert those markers to HTML span's here.
    if ( val === null || val === undefined )
        return val ;
    return val.replace( _HILITE_REGEXES[0], "<span class='hilite'>" )
              .replace( _HILITE_REGEXES[1], "</span>" ) ;
}

// --------------------------------------------------------------------

export function showInfoMsg( msg ) { _doShowNotificationMsg( "notice", msg ) ; }
export function showWarningMsg( msg ) { _doShowNotificationMsg( "warning", msg ) ; }
export function showErrorMsg( msg ) { _doShowNotificationMsg( "error", msg ) ; }

function _doShowNotificationMsg( msgType, msg )
{
    // show the notification message
    $.growl( {
        style: msgType,
        title: null,
        message: msg,
        location: "br",
        duration: (msgType == "warning") ? 15*1000 : 5*1000,
        fixed: (msgType == "error"),
    } ) ;
}

