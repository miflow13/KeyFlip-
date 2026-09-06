.PHONY: check package clean

check:
	python3 -m py_compile app.py src/keyflip/*.py
	/usr/bin/python3 -m unittest discover -s tests -v
	node --test tests/panel.test.cjs
	bash -n keyflip helper/keyflip-helper install.sh uninstall.sh scripts/build-release.sh
	desktop-file-validate packaging/io.github.miflow13.KeyFlip.desktop
	appstreamcli validate --no-net packaging/io.github.miflow13.KeyFlip.metainfo.xml
	glib-compile-schemas --strict --dry-run packaging

package: check
	./scripts/build-release.sh

clean:
	rm -rf __pycache__ dist
