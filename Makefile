.PHONY: check package clean

check:
	python3 -m py_compile app.py keyflip_app.py
	bash -n keyflip keyflip-helper install.sh uninstall.sh scripts/build-release.sh
	desktop-file-validate packaging/io.github.miflow13.KeyFlip.desktop
	appstreamcli validate --no-net packaging/io.github.miflow13.KeyFlip.metainfo.xml

package: check
	./scripts/build-release.sh

clean:
	rm -rf __pycache__ dist
