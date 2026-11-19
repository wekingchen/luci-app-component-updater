include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-component-updater
PKG_VERSION:=0.2.3
PKG_RELEASE:=1
PKG_LICENSE:=MIT
PKG_MAINTAINER:=wekingchen
PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)-$(PKG_VERSION)

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-component-updater
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=Generic component updater (NaiveProxy first)
  PKGARCH:=all
  DEPENDS:=+luci-base +rpcd +jsonfilter +libubox +opkg
endef

define Package/luci-app-component-updater/conffiles
/etc/config/component-updater
endef

define Package/luci-app-component-updater/description
  Config-driven GitHub component updater with official version discovery,
  precompressed native opkg IPKs, package-aware backup and rollback. No proxy configuration changes.
endef

define Build/Compile
endef

define Package/luci-app-component-updater/install
	$(CP) ./root/. $(1)/
	$(INSTALL_DIR) $(1)/www
	$(CP) ./htdocs/. $(1)/www/
	$(INSTALL_DIR) $(1)/etc/component-updater
	$(INSTALL_BIN) ./root/usr/sbin/component-updaterctl $(1)/usr/sbin/component-updaterctl
	$(INSTALL_BIN) ./root/usr/libexec/rpcd/component-updater $(1)/usr/libexec/rpcd/component-updater
endef

$(eval $(call BuildPackage,luci-app-component-updater))
