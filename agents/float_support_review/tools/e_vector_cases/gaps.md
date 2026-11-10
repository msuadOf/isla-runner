# RV64 浮点向量首轮样例缺口（2026-09-26）

后续验证状态：本表的 64 个 enum 缺口已在 `expanded-cases.json` / `expanded-results.json` 的映射×合法 SEW 批次补齐；状态与 rm 维度见 `README.md`。本表保留首轮调查时点，不再代表当前未测集合。

以 `clause-matrix.md` 的“其余 RVV clause 的 enum”附表为清单，并逐项核对 Sail `vext_fp_insts.sail`、`vext_fp_vm_insts.sail`、`vext_fp_red_insts.sail` 的 `encdec_*` 映射。首轮 `cases.json` 覆盖 16 个 enum clause 各一个成员；总计 80 个可列出的 enum 成员，已测 16 个，余 64 个。四个固定编码 clause（`VFMERGE`、`VFMV`、`VFMVFS`、`VFMVSF`）各有一个样例。

| Clause | 已测成员 | 尚未测试的 enum 成员 |
|---|---|---|
| `FVFMATYPE` | `VF_VMACC` | `VF_VMADD`, `VF_VNMADD`, `VF_VMSUB`, `VF_VNMSUB`, `VF_VNMACC`, `VF_VMSAC`, `VF_VNMSAC` |
| `FVFMTYPE` | `VFM_VMFNE` | `VFM_VMFEQ`, `VFM_VMFLE`, `VFM_VMFLT`, `VFM_VMFGT`, `VFM_VMFGE` |
| `FVFTYPE` | `VF_VADD` | `VF_VSUB`, `VF_VMIN`, `VF_VMAX`, `VF_VSGNJ`, `VF_VSGNJN`, `VF_VSGNJX`, `VF_VSLIDE1UP`, `VF_VSLIDE1DOWN`, `VF_VDIV`, `VF_VRDIV`, `VF_VMUL`, `VF_VRSUB` |
| `FVVMATYPE` | `FVV_VMACC` | `FVV_VMADD`, `FVV_VNMADD`, `FVV_VMSUB`, `FVV_VNMSUB`, `FVV_VNMACC`, `FVV_VMSAC`, `FVV_VNMSAC` |
| `FVVMTYPE` | `FVVM_VMFNE` | `FVVM_VMFEQ`, `FVVM_VMFLE`, `FVVM_VMFLT` |
| `FWFTYPE` | `FWF_VADD` | `FWF_VSUB` |
| `FWVFMATYPE` | `FWVF_VMACC` | `FWVF_VNMACC`, `FWVF_VMSAC`, `FWVF_VNMSAC` |
| `FWVFTYPE` | `FWVF_VADD` | `FWVF_VSUB`, `FWVF_VMUL` |
| `FWVTYPE` | `FWV_VADD` | `FWV_VSUB` |
| `FWVVMATYPE` | `FWVV_VMACC` | `FWVV_VNMACC`, `FWVV_VMSAC`, `FWVV_VNMSAC` |
| `FWVVTYPE` | `FWVV_VADD` | `FWVV_VSUB`, `FWVV_VMUL` |
| `RFVVTYPE` | `FVV_VFREDOSUM` | `FVV_VFREDUSUM`, `FVV_VFREDMAX`, `FVV_VFREDMIN` |
| `RFWVVTYPE` | `FVV_VFWREDOSUM` | `FVV_VFWREDUSUM` |
| `VFUNARY0` | `FV_CVT_X_F` | `FV_CVT_XU_F`, `FV_CVT_F_XU`, `FV_CVT_F_X`, `FV_CVT_RTZ_XU_F`, `FV_CVT_RTZ_X_F` |
| `VFUNARY1` | `FVV_VSQRT` | `FVV_VRSQRT7`, `FVV_VREC7`, `FVV_VCLASS` |
| `VFWUNARY0` | `FWV_CVT_F_F` | `FWV_CVT_XU_F`, `FWV_CVT_X_F`, `FWV_CVT_F_XU`, `FWV_CVT_F_X`, `FWV_CVT_RTZ_XU_F`, `FWV_CVT_RTZ_X_F` |

除 `VFMERGE` 固定 `vm=0` 外，首轮均为未掩码 `vm=1`、`SEW=32`、`LMUL=1`、`vl=1`、`vstart=0`；尚无 `SEW=16/64`、掩码关闭活动元素、`vstart>0`、`vl=0`、旧 `fflags` 累计、比较 NaN 或多元素归约的执行样例。首轮归约只测 ordered sum，宽化 unordered 与普通 unordered 尚未测；Sail 对宽化 ordered/unordered 共用顺序累加体，不能把两者的相同结果视为错误。

本清单描述未覆盖范围，不把尚未测试的成员记作失败或通过。新增样例须保留首轮 `cases.json`、`results.json` 和哈希证据，另存扩展批次。
