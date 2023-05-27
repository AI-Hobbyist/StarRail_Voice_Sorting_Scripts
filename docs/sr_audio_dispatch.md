# 浅析星穹铁道语音包分发规则

1. 登录时会请求分发，抓包易得此链接：https://prod-gf-cn-dp01.bhsr.com/query_gateway?version=CNPRODWin1.0.5&t=xxxxxxxxxx&uid=xxxxxxxxx&language_type=1&platform_type=3&dispatch_seed=xxxxxxxxxx&channel_id=1&sub_channel_id=2&is_need_url=1

2. Base64 解码返回 Body，可以得到：https://autopatchcn.bhsr.com/asb/V1.0Live/output_4186973_52d0b74c56

    > 在线加解密工具：https://gchq.github.io/CyberChef/

3. 接下来请求此链接，得到会动态分发的文件列表：https://autopatchcn.bhsr.com/asb/V1.0Live/output_4186973_52d0b74c56/client/Windows/Archive/M_ArchiveV.bytes

    ```
    {"MajorVersion":1,"MinorVersion":0,"PatchVersion":4186973,"ContentHash":"80dfbc0486030493dcbfe4d509609a9a","FileSize":1915108,"TimeStamp":1684185069,"FileName":"M_Start_AsbV","BaseAssetsDownloadUrl":"output_3829615_7dc8e76d36"}
    {"MajorVersion":1,"MinorVersion":0,"PatchVersion":4186973,"ContentHash":"30d67e6640842796d43971dce161a72b","FileSize":244,"TimeStamp":1684185068,"FileName":"M_Start_BlockV","BaseAssetsDownloadUrl":"output_3829615_7dc8e76d36"}
    {"MajorVersion":1,"MinorVersion":0,"PatchVersion":4186973,"ContentHash":"8b3d639359fa3c25e19fe1298feb6986","FileSize":7536640,"TimeStamp":1684185055,"FileName":"M_AsbV","BaseAssetsDownloadUrl":"output_3829615_7dc8e76d36"}
    {"MajorVersion":1,"MinorVersion":0,"PatchVersion":4186973,"ContentHash":"4a5abb0f82d8eba0b4d28139a199ac60","FileSize":35092,"TimeStamp":1684185053,"FileName":"M_BlockV","BaseAssetsDownloadUrl":"output_3829615_7dc8e76d36"}
    {"MajorVersion":1,"MinorVersion":0,"PatchVersion":4186973,"ContentHash":"b34e1d5532f9ee8042e6ecdbe83b4863","FileSize":45702,"TimeStamp":1684185092,"FileName":"M_AudioV","BaseAssetsDownloadUrl":"output_3829615_7dc8e76d36"}
    {"MajorVersion":1,"MinorVersion":0,"PatchVersion":4186973,"ContentHash":"b7fda4dd75ae258d59bcd6e9666d661e","FileSize":5531,"TimeStamp":1684185092,"FileName":"M_VideoV","BaseAssetsDownloadUrl":"output_3829615_7dc8e76d36"}
    ```
    注意其中的 ContentHash 和 BaseAssetsDownloadUrl 键值对

4. 就可以得到语音包索引的文件名 **AudioV_b34e1d5532f9ee8042e6ecdbe83b4863.bytes**
https://autopatchcn.bhsr.com/asb/V1.0Live/output_4186973_52d0b74c56/client/Windows/AudioBlock/AudioV_b34e1d5532f9ee8042e6ecdbe83b4863.bytes
    ```
    ...
    {"Path":"Chinese(PRC)/External0.pck","Md5":"8141dce6f5f76fecf6db6448db36e6bc","Size":44600606,"Patch":false,"SubPackId":0}
    {"Path":"Chinese(PRC)/External1.pck","Md5":"262cb689dd5efdf68b6730ce488a65fc","Size":45836089,"Patch":false,"SubPackId":0}
    {"Path":"Chinese(PRC)/External10.pck","Md5":"8a94463488c5def0996ac86fa4c5835a","Size":43600028,"Patch":false,"SubPackId":0}
    ...
    ```
    在该索引里就可以找到语音包 pck 的 Path 等信息，我们需要用到 Path 键值对拼凑链接。

5. 最后我们用在 **3** 中得到的 BaseUrl 和 **4** 中得到的 Path，即可轻松得到每个语音包的下载链接，如：
https://autopatchcn.bhsr.com/asb/V1.0Live/output_3829615_7dc8e76d36/client/Windows/AudioBlock/Chinese(PRC)/External0.pck

- 还可以通过已有索引匹配文件 MD5，检验完整性