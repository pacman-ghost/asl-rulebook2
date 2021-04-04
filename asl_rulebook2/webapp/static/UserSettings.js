export let gUserSettings = Cookies.getJSON( "user-settings" ) || {} ; //eslint-disable-line no-undef

// --------------------------------------------------------------------

export function saveUserSettings()
{
    // save the user settings
    Cookies.set( //eslint-disable-line no-undef
        "user-settings", gUserSettings,
        { SameSite: "strict", expires: 999 }
    ) ;
}
