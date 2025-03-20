
from esgvoc.core import service
import esgvoc.api as ev

def test_install():
    assert(service.config_manager is not None)
    before_test_active = service.config_manager.get_active_config_name()
    service.config_manager._init_registry()
    service.config_manager.switch_config("default")
    current_state = service.get_state()
    assert(current_state is not None)
    current_state.synchronize_all()
    assert(ev.valid_term("IPSL", "cmip6","institution_id","ipsl"))
    service.config_manager.switch_config(before_test_active)
    current_state = service.get_state()


def test_create_new_config():
    assert(service.config_manager is not None)
    before_test_active = service.config_manager.get_active_config_name()
    service.config_manager._init_registry()
    service.config_manager.switch_config("default")
    service.config_manager.save_config(service.config_manager.get_active_config().dump(),"default_test")
    service.config_manager.switch_config("default_test")
    current_state = service.get_state()
    assert(current_state is not None)
    current_state.synchronize_all()
    assert(ev.valid_term("IPSL", "cmip6","institution_id","ipsl"))
    service.config_manager.switch_config(before_test_active)
    current_state = service.get_state()




