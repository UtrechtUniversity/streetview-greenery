
    
class KrigeManager():
    def __init__(self, grid_level=0, tile_resolution=1024):
        
    def krige_map(self, window_range=1, overlay_name="greenery", upscale=2,
                  n_job=1, job_id=0, **kwargs):
        if self.green_mat is None:
            self.green_direct(**kwargs)

        tile_res = upscale*2**self.grid_level
        full_krige_map = np.zeros((
            tile_res*self.n_tiles_y,
            tile_res*self.n_tiles_x
            )
        )

        krige_dir = os.path.join("data.amsterdam", "krige",
                                 overlay_name + "-" + self.map_key)
        os.makedirs(krige_dir, exist_ok=True)
        vario_fp = os.path.join(krige_dir, "variogram.json")
        try:
            with open(vario_fp, "r") as fp:
                vario_kwargs = json.load(fp)
        except (FileNotFoundError, JSONDecodeError):
            vario_kwargs = _semivariance(self.green_mat, plot=False,
                                         variogram_model="exponential")
            with open(vario_fp, "w") as fp:
                json.dump(vario_kwargs, fp)

        pbar = tqdm(total=self.n_tiles_x*self.n_tiles_y)
        for iy, green_row in enumerate(self.green_mat):
            for ix, green_res in enumerate(green_row):
                pbar.update()
                if (iy*len(green_row)+ix) % n_job != job_id:
                    continue
                krige_fp = os.path.join(krige_dir,
                                        "krige_"+str(ix)+"_"+str(iy)+".json")
                try:
                    with open(krige_fp, "r") as fp:
                        krige = np.array(json.load(fp))
                except (FileNotFoundError, JSONDecodeError):
                    krige_green_res = _empty_green_res()
                    _extend_green_res(krige_green_res, green_res)
                    for idx in range(-window_range, window_range+1):
                        nix = ix + idx
                        if nix < 0 or nix >= self.n_tiles_x:
                            continue
                        for idy in range(-window_range, window_range+1):
                            niy = iy + idy
                            if niy < 0 or niy >= self.n_tiles_y:
                                continue
                            _extend_green_res(
                                krige_green_res, self.green_mat[niy][nix])
                    if (
                            len(krige_green_res) == 0 or
                            len(krige_green_res['green']) <= 1):
                        continue
                    x_start = self.x_start + ix*self.dx
                    x_end = x_start + self.dx
                    y_start = self.y_start + iy*self.dy
                    y_end = y_start + self.dy
                    long_grid = np.linspace(x_start, x_end, tile_res,
                                            endpoint=False)
                    lat_grid = np.linspace(y_start, y_end, tile_res,
                                           endpoint=False)
                    try:
                        krige = krige_greenery(krige_green_res, lat_grid,
                                               long_grid,
                                               init_kwargs=vario_kwargs)
                    except ValueError:
                        krige = np.zeros((tile_res, tile_res))
                    with open(krige_fp, "w") as fp:
                        json.dump(krige.tolist(), fp)

                full_krige_map[
                    iy*tile_res:(iy+1)*tile_res,
                    ix*tile_res:(ix+1)*tile_res
                    ] = krige
        pbar.close()
        full_long_grid = np.linspace(
            self.x_start, self.x_start+self.n_tiles_x*self.dx,
            tile_res*self.n_tiles_x, endpoint=False)
        full_lat_grid = np.linspace(
            self.y_start, self.y_start+self.n_tiles_y*self.dy,
            tile_res*self.n_tiles_y, endpoint=False)

        full_krige_map[full_krige_map < 0] = 0
        alpha_map = _alpha_from_coordinates(self.all_green_res, full_lat_grid,
                                            full_long_grid)
        overlay = MapImageOverlay(full_krige_map, lat_grid=full_lat_grid,
                                  long_grid=full_long_grid,
                                  alpha_map=alpha_map, name=overlay_name,
                                  min_green=0.0, max_green=1.0,
                                  cmap="RdYlGn")
        return overlay, self.map_key
