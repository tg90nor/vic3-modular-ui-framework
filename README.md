# Modular UI Framework

This mod aims to provide extension hooks for other mods to add their own UI elements to the game. It is designed to be as modular as possible, allowing for easy integration with other mods.
Just define one of the hooks as a type in your mods gui files and it will be shown in the game.

## Extension hooks list

### Sidebar

`gui/information_panel.gui`

The sidebar is not dynamic, so any new button needs to be added to this mod.

| Hook Name | Suggested Type | Description |
| --- | --- | --- |
| more_spreadsheets_sidebar_button | widget | More Spreadsheets sidebar button |
| cheat_menu_sidebar_button | widget | Cheat Menu sidebar button |

### Market Panel

`gui/market_panel.gui`

| Hook Name | Suggested Type | Description |
| --- | --- | --- |
| market_panel_header_top_left_button | widget | 30x30 button in the top left of the header, next to the Back button. |
| market_panel_header_bottom_left_button | widget | 30x30 button in the bottom left of the header, next to the Back button. |
| market_panel_details_content_override | container | Replaces the default Goods tab main content. |
| market_panel_trade_routes_content_override | container | Replaces the default Trade Routes tab main content. |
| market_panel_trade_routes_trade_suggestions_override | container | Replaces the default Highlights tab main content. |
| market_panel_states_content_override | container | Replaces the default Members tab main content. |

### States Panel

`gui/states_panel.gui`

| Hook Name | Suggested Type | Description |
| --- | --- | --- |
| states_panel_header_top_left_button | widget | 30x30 button in the top left of the header, next to the Back button. |
| states_panel_header_bottom_left_button | widget | 30x30 button in the bottom left of the header, next to the Back button. |
| states_panel_overview_content_override | flowcontainer | Replaces the default Overview tab main content. |
| states_panel_condensed_override | flowcontainer | Replaces the condensed version of the Overview tab, which is not normally accessible. |
| states_panel_buildings_content_override | flowcontainer | Replaces the default Buildings tab main content. |
| states_panel_population_content_override | flowcontainer | Replaces the default Population tab main content. |
| state_panel_local_goods_content_override | flowcontainer | Replaces the default Local Prices tab main content. |
| state_panel_modifiers_content_override | flowcontainer | Replaces the default Information tab main content. |

## How to use

Say I have a mod called "MyMod" and I want to add a button to the top left of the Market Panel header.

I could create gui/my_mod.gui file with the following content:
```
types my_mod {
  type market_panel_header_top_left_button = widget {
    # inactive variant
    button_icon_round = {
      size = { 100% 100% }
      tooltip = "MY_MOD_BUTTON_TOOLTIP"
      using = confirm_button_sound
      visible = "[Not(GetPlayer.MakeScope.Var('toggle_my_mod_function').IsSet)]"
      onclick = "[GetScriptedGui('toggle_my_mod_function').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]"
      blockoverride "icon" {
        texture = "gfx/interface/buttons/button_icons/list.dds"
      }
    }
    # active variant
    button_icon_round_action = {
      size = { 100% 100%}
      tooltip = "MY_MOD_BUTTON_TOOLTIP"
      using = confirm_button_sound
      visible = "[GetPlayer.MakeScope.Var('toggle_my_mod_function').IsSet]"
      onclick = "[GetScriptedGui('toggle_my_mod_function').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]"
      blockoverride "icon" {
        texture = "gfx/interface/buttons/button_icons/list.dds"
      }
      using = selected_sidepanel_animation_small_no_arrow
    }
  }
}
```
