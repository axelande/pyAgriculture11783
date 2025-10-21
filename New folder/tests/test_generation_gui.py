from PySide2 import QtCore
import pytest
from pyAgriculture.generate_taskdata import GenerateTaskData
from pyAgriculture.create_recpie import CreateRecipe


@pytest.fixture
def gtd(qtbot):
    test_gtd = GenerateTaskData()
    qtbot.addWidget(test_gtd)
    return test_gtd


@pytest.fixture
def recipe(qtbot, gtd):
    test_recipe = CreateRecipe(gtd)
    qtbot.addWidget(test_recipe)
    return test_recipe


def test_schemas_correct_format(gtd):
    assert type(gtd.schemas) == dict


def test_adding_and_removal_of_items(qtbot, recipe):
    item = recipe.available_schemas_list.item(3, 0)
    assert item is not None
    rect = recipe.available_schemas_list.visualItemRect(item)
    qtbot.mouseClick(recipe.available_schemas_list.viewport(), QtCore.Qt.RightButton, pos=rect.center())
    recipe.add_item_button.click()
    assert recipe.included_schemas_list.rowCount() == 1
    recipe.included_schemas_list.selectRow(0)
    recipe.remove_item_button.click()
    assert recipe.included_schemas_list.rowCount() == 0


def test_adding_to_attributes(qtbot, recipe):
    item = recipe.available_schemas_list.item(3, 0)
    rect = recipe.available_schemas_list.visualItemRect(item)
    qtbot.mouseClick(recipe.available_schemas_list.viewport(), QtCore.Qt.RightButton, pos=rect.center())
    recipe.add_item_button.click()
    recipe.continue_button.click()
    assert recipe.available_attributes_list.rowCount() > 0


def test_saving_of_data(qtbot, recipe, tmpdir):
    path = tmpdir + 'test.recipe'
    item = recipe.available_schemas_list.item(10, 0)
    rect = recipe.available_schemas_list.visualItemRect(item)
    qtbot.mouseClick(recipe.available_schemas_list.viewport(), QtCore.Qt.RightButton, pos=rect.center())
    recipe.add_item_button.click()
    recipe.continue_button.click()
    recipe.store_data(path=path)
