import { ReactNode } from 'react';
import { App, ConfigProvider, theme, ThemeConfig } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { goldDark, greenDark, redDark, slateDark } from '@radix-ui/colors';

const studioTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: goldDark.gold9, colorPrimaryHover: goldDark.gold10,
    colorPrimaryActive: goldDark.gold10, colorPrimaryBg: goldDark.gold3,
    colorPrimaryBgHover: goldDark.gold4, colorPrimaryBorder: goldDark.gold7,
    colorPrimaryBorderHover: goldDark.gold8, colorPrimaryText: goldDark.gold11,
    colorPrimaryTextHover: goldDark.gold12, colorPrimaryTextActive: goldDark.gold12,
    colorInfo: goldDark.gold9, colorSuccess: greenDark.green9,
    colorWarning: goldDark.gold9, colorError: redDark.red9,
    colorErrorBg: redDark.red3, colorErrorBorder: redDark.red7, colorErrorText: redDark.red11,
    colorErrorTextHover: redDark.red12, colorErrorTextActive: redDark.red12,
    colorBgBase: slateDark.slate1, colorBgContainer: slateDark.slate2,
    colorBgElevated: slateDark.slate3, colorBgLayout: slateDark.slate1,
    colorBgContainerDisabled: slateDark.slate3,
    colorBorder: slateDark.slate7, colorBorderSecondary: slateDark.slate6,
    colorText: slateDark.slate12, colorTextBase: slateDark.slate12,
    colorTextSecondary: slateDark.slate11, colorTextTertiary: slateDark.slate11,
    colorTextQuaternary: slateDark.slate11, colorTextDisabled: slateDark.slate11,
    colorTextPlaceholder: slateDark.slate11, colorTextLightSolid: goldDark.gold12,
    colorFill: slateDark.slate5, colorFillSecondary: slateDark.slate4,
    colorFillTertiary: slateDark.slate3, colorFillQuaternary: slateDark.slate2,
    controlOutline: goldDark.gold8, controlItemBgHover: slateDark.slate4,
    controlItemBgActive: goldDark.gold5, controlItemBgActiveHover: goldDark.gold4,
    fontFamily: 'Inter, "Segoe UI", "Microsoft YaHei", sans-serif',
    fontSize: 12, fontSizeSM: 12, fontSizeLG: 14, fontSizeXL: 20,
    fontSizeHeading1: 28, fontSizeHeading2: 20, fontSizeHeading3: 20,
    fontSizeHeading4: 14, fontSizeHeading5: 14,
    lineWidth: 0.5, borderRadius: 4, borderRadiusLG: 6, borderRadiusSM: 4,
    boxShadow: 'none', boxShadowSecondary: 'none', boxShadowTertiary: 'none',
    motion: false, motionDurationFast: '0.25s', motionDurationMid: '0.25s',
    motionDurationSlow: '0.25s', motionEaseInOut: 'ease-out',
  },
  components: {
    Button: {defaultBg: slateDark.slate3, defaultHoverBg: slateDark.slate4,
      defaultActiveBg: slateDark.slate5, defaultColor: slateDark.slate12,
      defaultHoverColor: slateDark.slate12, defaultBorderColor: slateDark.slate7,
      defaultHoverBorderColor: slateDark.slate8, defaultShadow: 'none', primaryShadow: 'none', dangerShadow: 'none'},
    Modal: {titleFontSize: 20},
  },
};
export function UiProvider({children}: {children: ReactNode}) {
  return <ConfigProvider locale={zhCN} theme={studioTheme} button={{autoInsertSpace:false}}><App>{children}</App></ConfigProvider>;
}
